import pandas as pd
from bokeh import (embed, layouts, models)
from pathlib import Path
from html import unescape
from os.path import join as opj
from string import Template
from tedana.info import __version__
from tedana.reporting import dynamic_figures as df


def _update_template_about(call, methods):
    """
    Populate a report with content.

    Parameters
    ----------
    call : str
        Call used to execute tedana
    methods : str
        Generated methods for specific tedana call
    Returns
    -------
    HTMLReport : an instance of a populated HTML report
    """
    resource_path = Path(__file__).resolve().parent.joinpath('data', 'html')
    body_template_name = 'report_body_template.html'
    body_template_path = resource_path.joinpath(body_template_name)
    with open(str(body_template_path), 'r') as body_file:
        body_tpl = Template(body_file.read())
    subst = body_tpl.substitute(content=methods,
                                javascript=None)
    body = unescape(subst)
    return body


def _update_template_bokeh(bokeh_id, bokeh_js):
    """
    Populate a report with content.

    Parameters
    ----------
    bokeh_id : str
        HTML div created by bokeh.embed.components
    bokeh_js : str
        Javascript created by bokeh.embed.components
    Returns
    -------
    HTMLReport : an instance of a populated HTML report
    """
    resource_path = Path(__file__).resolve().parent.joinpath('data', 'html')

    body_template_name = 'report_body_template.html'
    body_template_path = resource_path.joinpath(body_template_name)
    with open(str(body_template_path), 'r') as body_file:
        body_tpl = Template(body_file.read())
    subst = body_tpl.substitute(content=bokeh_id,
                                javascript=bokeh_js)
    body = unescape(subst)
    return body


def _save_as_html(body):
    """
    Save an HTML report out to a file.

    Parameters
    ----------
    body : str
        Body for HTML report with embedded figures
    """
    resource_path = Path(__file__).resolve().parent.joinpath('data', 'html')
    head_template_name = 'report_head_template.html'
    head_template_path = resource_path.joinpath(head_template_name)
    with open(str(head_template_path), 'r') as head_file:
        head_tpl = Template(head_file.read())

    html = head_tpl.substitute(version=__version__, body=body)
    return html


def generate_report(bokeh_id, bokeh_js, file_path=None):
    """
    Generate and save an HTML report.

    Parameters
    ----------
    bokeh_id : str
        HTML div created by bokeh.embed.components
    bokeh_js : strs
        Javascript created by bokeh.embed.components
    file_path : str
        The file path on disk to write the HTML report

    Returns
    -------
    HTML : file
        A generated HTML report
    """
    body = _update_template_bokeh(bokeh_id, bokeh_js)
    html = _save_as_html(body)

    if file_path is not None:
        with open(file_path, 'wb') as f:
            f.write(html.encode('utf-8'))
    else:
        with open('./tedana_report.html', 'wb') as f:
            f.write(html.encode('utf-8'))


def html_report(out_dir, tr):
    # Load the component time series
    comp_ts_path = opj(out_dir, 'ica_mixing.tsv')
    comp_ts_df = pd.read_csv(comp_ts_path, sep='\t', encoding='utf=8')
    n_vols, n_comps = comp_ts_df.shape

    # Load the component table
    comptable_path = opj(out_dir, 'ica_decomposition.json')
    comptable_cds = df._create_data_struct(comptable_path)

    # Create kappa rho plot
    kappa_rho_plot = df._create_kr_plt(comptable_cds)

    # Create sorted plots
    kappa_sorted_plot = df._create_sorted_plt(comptable_cds, n_comps,
                                              'kappa_rank', 'kappa',
                                              'Kappa Rank', 'Kappa')
    rho_sorted_plot = df._create_sorted_plt(comptable_cds, n_comps,
                                            'rho_rank', 'rho',
                                            'Rho Rank', 'Rho')
    varexp_pie_plot = df._create_varexp_pie_plt(comptable_cds, n_comps)

    # link all dynamic figures
    figs = [kappa_rho_plot, kappa_sorted_plot,
            rho_sorted_plot, varexp_pie_plot]

    div_content = models.Div(width=600, height=900, height_policy='fixed')

    for fig in figs:
        df._link_figures(fig, comptable_cds, div_content, out_dir=out_dir)

    # Create a layout
    app = layouts.column(layouts.row(kappa_rho_plot, kappa_sorted_plot,
                                     rho_sorted_plot, varexp_pie_plot),
                         div_content)

    # Embed for reporting
    kr_script, kr_div = embed.components(app)
    generate_report(kr_div, kr_script,
                    file_path=opj(out_dir, 'report_v3.html'))
