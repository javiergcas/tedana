# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.2'
#       jupytext_version: 1.2.4
#   kernelspec:
#     display_name: tedana-hack
#     language: python
#     name: tedana-hack
# ---

# %%
import holoviews as hv
hv.extension('bokeh')

# %%
import pandas as pd
import numpy as np
from os.path import join as opj
from math import pi
from sklearn.preprocessing import MinMaxScaler
from bokeh import (embed, events, layouts, models, plotting, transform)
from tedana import (reporting, utils)

color_mapping = {'accepted': '#2ecc71',
                 'rejected': '#e74c3c',
                 'ignored': '#3498db'}


# %%
def _link_figures(fig, comptable_ds,
                  ts_src, fft_src, ts_plot, fft_plot,
                  ts_line_glyph, fft_line_glyph,
                  div_content, out_dir):
    """
    Links figures and adds interaction on mouse-click.

    Parameters
    ----------
    fig : bokeh.plotting.figure
        Figure containing a given plot

    comptable_ds : bokeh.models.ColumnDataSource
        Data structure with a limited version of the comptable
        suitable for dynamic plot purposes

    ts_src : bokeh.models.ColumnDataSource
        Data structure containing the timeseries for all
        components

    fft_src : bokeh.models.ColumnDataSource
        Data structure containing the fft for all components

    ts_plot : bokeh.models.ColumnDataSource
        Data structure that contains the timeseries being
        plotted at a given moment.

    fft_plot : bokeh.models.ColumnDataSource
        Data structure that contains the fft being plotted
        at a given moment in time

    ts_line_glyph : bokeh.models.Line
        Link to the line element of the time series plot.
        Needed to update the color of the timeseries trace.

    fft_line_glyph : bokeh.models.Line
        Link to the line element of the fft plot.
        Needed to update the color of the fft trace.

    div_content : bokeh.models.Div
        Div element for additional HTML content.

    out_dir : str
        Output directory of tedana results.

    Returns
    -------
    fig : bokeh.plotting.figure
        Same as input figure, but with a linked method to
        its Tap event.

    """
    fig.js_on_event(events.Tap,
                    tap_callback(comptable_ds,
                                 ts_src,
                                 fft_src,
                                 ts_plot,
                                 fft_plot,
                                 ts_line_glyph,
                                 fft_line_glyph,
                                 div_content,
                                 out_dir))
    return fig


# %%
def _create_ts_plot(n_vol):
    """
    Generates a bokeh line plot for the time series of a given component

    Parameters
    ----------
    n_vols: float
        Number of acquisitions

    Returns
    -------
    fig: bokeh.plotting.figure.Figure
        Bokeh plot to show a given component time series

    line_glyph: bokeh.models.Line
        Link to the line element of the time series plot.

    ts_cds: bokeh.models.ColumnDataSource
        Data structure that contains the timeseries being
        plotted at a given moment.
    """

    ts_cds = models.ColumnDataSource(data=dict(x=np.arange(n_vol),
                                               y=np.zeros(n_vol,)))

    fig = plotting.figure(plot_width=800, plot_height=200,
                          tools=["wheel_zoom,box_zoom,reset,pan,crosshair,save",
                                 models.HoverTool(tooltips=[('Volume', '@x{0.00}'),
                                                            ('Signal', '@y{0.00}')])],
                          title="Component Time Series")
    line_glyph = models.Line(x='x', y='y', line_color='#000000', line_width=3)
    fig.add_glyph(ts_cds, line_glyph)
    fig.xaxis.axis_label = 'Time [Volume]'
    fig.yaxis.axis_label = 'Signal'
    fig.toolbar.logo = None
    fig.toolbar_location = 'above'
    fig.x_range = models.Range1d(0, n_vol)
    return fig, line_glyph, ts_cds


# %%
def _create_fft_plot(freqs):
    """
    Generates a bokeh line plot for the spectrum of a given component

    Parameters
    ----------
    freqs: np.darray
        List of frequencies for which spectral amplitude values are
        available

    Returns
    -------
    fig: bokeh.plotting.figure.Figure
        Bokeh plot to show a given component spectrum

    line_glyph: bokeh.models.Line
        Link to the line element of the fft plot.

    ts_cds: bokeh.models.ColumnDataSource
        Data structure that contains the fft being
        plotted at a given moment.
    """
    Nf = len(freqs)
    max_freq = np.max(freqs)
    fft_cds = models.ColumnDataSource(data=dict(x=freqs, y=np.zeros(Nf,)))
    fig = plotting.figure(plot_width=800, plot_height=200,
                          tools=["wheel_zoom,box_zoom,reset,pan,crosshair,save",
                                 models.HoverTool(tooltips=[('Freq.', '@x{0.000} Hz'),
                                                            ('Power', '@y{0.00}')])],
                          title="Component Spectrum")
    line_glyph = models.Line(x='x', y='y', line_color='#000000', line_width=3)
    fig.add_glyph(fft_cds, line_glyph)
    fig.xaxis.axis_label = 'Frequency [Hz]'
    fig.yaxis.axis_label = 'Power'
    fig.toolbar.logo = None
    fig.toolbar_location = 'above'
    fig.x_range = models.Range1d(0, max_freq)
    return fig, line_glyph, fft_cds


# %%
def _spectrum_data_src(comp_ts_cds, tr, n_comps):
    """
    Computes FFT for all time series and puts them on a bokeh.models.ColumnDataSource

    Parameters
    ----------
    comp_ts_cds: bokeh.models.ColumnDataSource
        Contains the time series for all components
    tr: int
        Data Repetition Time in seconds
    n_comps: int
        Number of components

    Returns
    -------
    cds: bokeh.models.ColumnDataSource
        Contains the spectrum for all time series
    freqs: np.darray
        List of frequencies for which spectral amplitude values are
        available
    """
    spectrum, freqs = utils.get_spectrum(comp_ts_cds.data['ica_00'], tr)
    n_freqs = spectrum.shape[0]
    df = pd.DataFrame(columns=['ica_' + str(c).zfill(2) for c in np.arange(n_comps)],
                      index=np.arange(n_freqs))
    for c in np.arange(n_comps):
        cid = 'ica_' + str(c).zfill(2)
        ts = comp_ts_cds.data[cid]
        spectrum, freqs = utils.get_spectrum(ts, tr)
        df[cid] = spectrum
    cds = models.ColumnDataSource(df)
    return cds, freqs


# %%
def create_data_struct(comptable_path, color_mapping=color_mapping):
    """
    Create Bokeh ColumnDataSource with all info dynamic plots need

    Parameters
    ----------
    comptable: str
        file path to component table, JSON format

    Returns
    -------
    cds: bokeh.models.ColumnDataSource
        Data structure with all the fields to plot or hover over
    """
    unused_cols = ['normalized variance explained',
                   'countsigFR2', 'countsigFS0',
                   'dice_FS0', 'countnoise', 'dice_FR2',
                   'signal-noise_t', 'signal-noise_p',
                   'd_table_score', 'kappa ratio',
                   'rationale', 'd_table_score_scrub']

    df = pd.read_json(comptable_path)
    df.drop('Description', axis=0, inplace=True)
    df.drop('Method', axis=1, inplace=True)
    df = df.T
    n_comps = df.shape[0]

    # remove space from column name
    df.rename(columns={'variance explained': 'var_exp'}, inplace=True)

    # For providing sizes based on Var Explained that are visible
    mm_scaler = MinMaxScaler(feature_range=(4, 20))
    df['var_exp_size'] = mm_scaler.fit_transform(
        df[['var_exp', 'normalized variance explained']])[:, 0]

    # Calculate Kappa and Rho ranks
    df['rho_rank'] = df['rho'].rank(ascending=False).values
    df['kappa_rank'] = df['kappa'].rank(ascending=False).values
    df['var_exp_rank'] = df['var_exp'].rank(ascending=False).values

    # Remove unsed columns to decrease size of final HTML
    df.drop(unused_cols, axis=1, inplace=True)

    # Create additional Column with colors based on final classification
    df['color'] = [color_mapping[i] for i in df['classification']]

    # Create additional column with component ID
    df['component'] = np.arange(n_comps)

    # Compute angle and re-sort data for Pie plots
    df['angle'] = df['var_exp'] / df['var_exp'].sum() * 2 * pi
    df.sort_values(by=['classification', 'var_exp'], inplace=True)

    cds = models.ColumnDataSource(data=dict(
        kappa=df['kappa'],
        rho=df['rho'],
        varexp=df['var_exp'],
        kappa_rank=df['kappa_rank'],
        rho_rank=df['rho_rank'],
        varexp_rank=df['var_exp_rank'],
        component=[str(i) for i in df['component']],
        color=df['color'],
        size=df['var_exp_size'],
        classif=df['classification'],
        angle=df['angle']))

    return cds


# %%
tap_callback_jscode = """
    // Accessing the selected component ID
    var data          = source_comp_table.data;
    var selected_idx = source_comp_table.selected.indices;
    if(selected_idx > 0) {
        // A component has been selected
        // -----------------------------
        var components = data['component']
        var selected = components[selected_idx]
        var selected_padded = '' + selected;
        while (selected_padded.length < 2) {
            selected_padded = '0' + selected_padded;
        }
        var selected_padded_forIMG = '0' + selected_padded
        var selected_padded_C = 'ica_' + selected_padded

        // Find color for selected component
        var colors = data['color']
        var this_component_color = colors[selected_idx]

        // Update time series line color
        ts_line.line_color = this_component_color;

        // Update spectrum line color
        fft_line.line_color = this_component_color;

        // Updating TS Plot
        var Plot_TS = source_tsplot.data;
        var TS_x    = Plot_TS['x']
        var TS_y    = Plot_TS['y']
        var Comp_TS   = source_meica_ts.data;
        var Comp_TS_y = Comp_TS[selected_padded_C]

        for (var i = 0; i < TS_x.length; i ++) {
            TS_y[i] = Comp_TS_y[i]
        }
        source_tsplot.change.emit();

        // Updating FFT Plot
        var Plot_FFT = source_fftplot.data;
        var FFT_x = Plot_FFT['x']
        var FFT_y = Plot_FFT['y']
        var Comp_FFT = source_meica_fft.data;
        var Comp_FFT_y = Comp_FFT[selected_padded_C]
        for (var i = 0; i < FFT_x.length; i ++) {
            FFT_y[i] = Comp_FFT_y[i]
        }
        source_fftplot.change.emit();

        // Image Below Plots
        div.text = ""
        var line = "<span><img src='" + outdir + "/figures/comp_"+selected_padded_forIMG+".png'" +
            " alt='Component Map' height=1000 width=900><span>\\n";
        console.log('Linea: ' + line)
        var text = div.text.concat(line);
        var lines = text.split("\\n")
            if (lines.length > 35)
                lines.shift();
        div.text = lines.join("\\n");

    } else {
        // No component has been selected
        // ------------------------------
        // Set Component color to Black
        var this_component_color = '#000000'

        // Update time series line color
        ts_line.line_color = this_component_color;

        // Update spectrum line color
        fft_line.line_color = this_component_color;

        // Updating TS Plot
        var Plot_TS = source_tsplot.data;
        var TS_x    = Plot_TS['x']
        var TS_y    = Plot_TS['y']
        for (var i = 0; i < TS_x.length; i ++) {
            TS_y[i] = 0
        }
        source_tsplot.change.emit();

        // Updating FFT Plot
        var Plot_FFT = source_fftplot.data;
        var FFT_x = Plot_FFT['x']
        var FFT_y = Plot_FFT['y']
        for (var i = 0; i < FFT_x.length; i ++) {
            FFT_y[i] = 0
        }
        source_fftplot.change.emit();

        // Image Below Plots
        div.text = "\\n"

    }
    """


def tap_callback(comptable_cds, CDS_meica_ts, comp_fft_cds, plot_ts_cds,
                 plot_fft_cds, ts_line_glyph, fft_line_glyph, div, out_dir):
    """
    Javacript function to animate tap events and show component info on the right

    Parameters
    ----------
    CDS: bokeh.models.ColumnDataSource
        Data structure containing a limited set of columns from the comp_table
    div: bokeh.models.Div
        Target Div element where component images will be loaded

    Returns
    -------
    CustomJS: bokeh.models.CustomJS
        Javascript function that adds the tapping functionality
    """
    return models.CustomJS(args=dict(source_comp_table=comptable_cds,
                                     source_meica_ts=CDS_meica_ts,
                                     source_tsplot=plot_ts_cds,
                                     source_meica_fft=comp_fft_cds,
                                     source_fftplot=plot_fft_cds,
                                     div=div_content,
                                     ts_line=ts_line_glyph,
                                     fft_line=fft_line_glyph,
                                     outdir=out_dir), code=tap_callback_jscode)


# %%
def create_kr_plt(comptable_cds):
    """
    Create Dymamic Kappa/Rho Scatter Plot

    Parameters
    ----------
    comptable_cds: bokeh.models.ColumnDataSource
        Data structure containing a limited set of columns from the comp_table

    Returns
    -------
    fig: bokeh.plotting.figure.Figure
        Bokeh scatter plot of kappa vs. rho
    """
    # Create Panel for the Kappa - Rho Scatter
    kr_hovertool = models.HoverTool(tooltips=[('Component ID', '@component'),
                                              ('Kappa', '@kappa{0.00}'),
                                              ('Rho', '@rho{0.00}'),
                                              ('Var. Expl.', '@varexp{0.00}%')])
    fig = plotting.figure(plot_width=400, plot_height=400,
                          tools=["tap,wheel_zoom,reset,pan,crosshair,save", kr_hovertool],
                          title="Kappa / Rho Plot")
    fig.circle('kappa', 'rho', size='size', color='color', alpha=0.5, source=comptable_cds,
               legend_group='classif')
    fig.xaxis.axis_label = 'Kappa'
    fig.yaxis.axis_label = 'Rho'
    fig.toolbar.logo = None
    fig.legend.background_fill_alpha = 0.5
    fig.legend.orientation = 'horizontal'
    fig.legend.location = 'bottom_right'
    return fig


# %%
def create_sorted_plt(compatable_cds, n_comps, x_var, y_var, title=None,
                      x_label=None, y_label=None):
    """
    Create dynamic sorted plots

    Parameters
    ----------
    comptable_ds: bokeh.models.ColumnDataSource
        Data structure containing a limited set of columns from the comp_table

    x_var: str
        Name of variable for the x-axis

    y_var: str
        Name of variable for the y-axis

    title: str
        Plot title

    x_label: str
        X-axis label

    y_label: str
        Y-axis label

    Returns
    -------
    fig: bokeh.plotting.figure.Figure
        Bokeh plot of components ranked by a given feature
    """
    hovertool = models.HoverTool(tooltips=[('Component ID', '@component'),
                                           ('Kappa', '@kappa{0.00}'),
                                           ('Rho', '@rho{0.00}'),
                                           ('Var. Expl.', '@varexp{0.00}%')])
    fig = plotting.figure(plot_width=400, plot_height=400,
                          tools=["tap,wheel_zoom,reset,pan,crosshair,save", hovertool],
                          title=title)
    fig.line(x=np.arange(1, n_comps + 1),
             y=comptable_cds.data[y_var].sort_values(ascending=False).values,
             color='black')
    fig.circle(x_var, y_var, source=comptable_cds,
               size=5, color='color', alpha=0.7)
    fig.xaxis.axis_label = x_label
    fig.yaxis.axis_label = y_label
    fig.x_range = models.Range1d(-1, n_comps + 1)
    fig.toolbar.logo = None

    return fig


# %%
def create_varexp_pie_plt(comptable_cds, n_comps):
    fig = plotting.figure(plot_width=400, plot_height=400, title='Variance Explained View',
                          tools=['hover,tap,save'],
                          tooltips=[('Component ID', ' @component'),
                                    ('Kappa', '@kappa{0.00}'),
                                    ('Rho', '@rho{0.00}'),
                                    ('Var. Exp.', '@varexp{0.00}%')])
    fig.wedge(x=0, y=1, radius=.9,
              start_angle=transform.cumsum('angle', include_zero=True),
              end_angle=transform.cumsum('angle'),
              line_color="white",
              fill_color='color', source=comptable_cds, fill_alpha=0.7)
    fig.axis.visible = False
    fig.grid.visible = False
    fig.toolbar.logo = None

    circle = models.Circle(x=0, y=1, size=150, fill_color='white', line_color='white')
    fig.add_glyph(circle)

    return fig


# %%
# -------------------------------------------------------------------------

out_dir = '/opt/tedana-hack/tedana/docs/DynReports/data/TED.five-echo/'
tr = 2

# Load the component time series
comp_ts_path = opj(out_dir, 'ica_mixing.tsv')
comp_ts_df = pd.read_csv(comp_ts_path, sep='\t', encoding='utf=8')
n_vols, n_comps = comp_ts_df.shape
comp_ts_df['Volume'] = np.arange(n_vols)
comp_ts_cds = models.ColumnDataSource(comp_ts_df)

# Load the component table
comptable_path = opj(out_dir, 'ica_decomposition.json')
comptable_cds = create_data_struct(comptable_path)

# Generate the component's spectra
comp_fft_cds, freqs = _spectrum_data_src(comp_ts_cds, tr, n_comps)

# Create ts, fft plots
ts_plot, ts_line_glyph, plot_ts_cds = _create_ts_plot(n_vols)
fft_plot, fft_line_glyph, plot_fft_cds = _create_fft_plot(freqs)

# Create kappa rho plot
kappa_rho_plot = create_kr_plt(comptable_cds)

# Create sorted plots
kappa_sorted_plot = create_sorted_plt(comptable_cds, n_comps,
                                      'kappa_rank', 'kappa',
                                      'Kappa Rank', 'Kappa')
rho_sorted_plot = create_sorted_plt(comptable_cds, n_comps,
                                    'rho_rank', 'rho',
                                    'Rho Rank', 'Rho')
varexp_pie_plot = create_varexp_pie_plt(comptable_cds, n_comps)

# link all dynamic figures
figs = [kappa_rho_plot, kappa_sorted_plot,
        rho_sorted_plot, varexp_pie_plot]

div_content = models.Div(width=600, height=900, height_policy='fixed')

for fig in figs:
    _link_figures(fig, comptable_cds, comp_ts_cds, comp_fft_cds,
                  plot_ts_cds, plot_fft_cds, ts_line_glyph,
                  fft_line_glyph, div_content, out_dir)


# Create a layout
app = layouts.column(layouts.row(kappa_rho_plot, kappa_sorted_plot,
                                 rho_sorted_plot, varexp_pie_plot),
                     layouts.row(ts_plot, fft_plot),
                     div_content)

# Embed for reporting
kr_script, kr_div = embed.components(app)
reporting.generate_report(kr_div, kr_script,
                          file_path='/opt/report_v3.html')
