import numpy as np
import time
import tqdm
import plotly.express as px
from dash_bootstrap_templates import load_figure_template

load_figure_template(["cyborg", "darkly", "minty", "cerulean"])


class GraphsCalculator:
    def __init__(self):
        self._fig_histogram_annotation_by_item = None
        self._fig_pie_annotation_type = None
        self._fig_bar_annotations_labels = None
        self._fig_scatter_item_height_width = None
        self._fig_sunburst_annotation_attribute_by_label = None
        self._fig_heatmap_annotation_location = None
        self._fig_scatter_annotation_height_width = None
        self._fig_pie_annotation_attributes = None

    def clear(self):
        self._fig_histogram_annotation_by_item = None
        self._fig_pie_annotation_type = None
        self._fig_bar_annotations_labels = None
        self._fig_scatter_item_height_width = None
        self._fig_sunburst_annotation_attribute_by_label = None
        self._fig_heatmap_annotation_location = None
        self._fig_scatter_annotation_height_width = None
        self._fig_pie_annotation_attributes = None

    def histogram_annotation_by_item(self, df, settings):
        if self._fig_histogram_annotation_by_item is None:
            group_counts = df.groupby('item_id').size().reset_index(name='counts')
            fig = px.histogram(x=group_counts.values[:, 1],
                               title='Number of Annotations by Items',
                               nbins=group_counts.values[:, 1].max())
            self._fig_histogram_annotation_by_item = fig
        else:
            fig = self._fig_histogram_annotation_by_item

        fig.update_layout(xaxis1=dict(title='# Items'),
                          yaxis1=dict(title='# Annotations'),
                          )
        # fig.show('browser')
        return fig

    def pie_annotation_type(self, df, settings):  # 1, 2
        if self._fig_pie_annotation_type is None:
            type_value_counts = df['type'].value_counts()

            fig = px.pie(labels=type_value_counts.index,
                         values=type_value_counts.values,
                         names=list(type_value_counts.index),
                         hole=0.3,
                         title="Annotation Type",
                         )
            fig.update_traces(textposition='outside',
                              textinfo='percent+label',
                              marker=dict(line=dict(color='#ffffff',
                                                    width=2)),
                              # pull=[0.05, 0, 0.03],
                              opacity=0.9,
                              # rotation=180
                              )
            self._fig_pie_annotation_type = fig
        else:
            fig = self._fig_pie_annotation_type

        return fig

    def bar_annotations_labels(self, df, settings):
        if self._fig_bar_annotations_labels is None:
            label_value_counts = df['label'].value_counts()
            fig = px.bar(x=label_value_counts.index,
                         y=label_value_counts.values,
                         title="Annotation Labels Histogram"
                         )
            self._fig_bar_annotations_labels = fig
        else:
            fig = self._fig_bar_annotations_labels
        fig.update_layout(template=settings['theme'])

        return fig

    def scatter_item_height_width(self, df, settings):
        if self._fig_scatter_item_height_width is None:
            a = df.groupby(['width', 'height']).size().reset_index(name='Counts')
            a['hover_text'] = [f'Count: {count}' for count in a['Counts']]
            fig = px.scatter(data_frame=a,
                             title="Item Height/Width",
                             x='height',
                             y='width',
                             size='Counts',
                             hover_name='hover_text',  # Set hover text
                             )
            fig.update_traces(marker=dict(sizemode='area',
                                          sizeref=2. * max(a['Counts']) / (40. ** 2),
                                          sizemin=4))
            fig.update_xaxes(range=[0, df['height'].max()],
                             title='Height')  # Set min x to 0 and max x to 40
            fig.update_yaxes(range=[0, df['width'].max()],
                             title='Width')  # Set min x to 0 and max x to 40
            self._fig_scatter_item_height_width = fig
        else:
            fig = self._fig_scatter_item_height_width
        fig.update_layout(template=settings['theme'])

        return fig

    def pie_annotation_attributes(self, df, settings):
        if self._fig_pie_annotation_attributes is None:
            attributes_value_counts = df['attributes'].value_counts()

            fig = px.pie(labels=list(attributes_value_counts.index),
                         values=attributes_value_counts.values,
                         names=list(attributes_value_counts.index),
                         title="Annotation Attribute",
                         hole=0.3,
                         )
            fig.update_traces(textposition='outside',
                              textinfo='percent+label',
                              marker=dict(line=dict(color='#ffffff',
                                                    width=2)),
                              # pull=[0.05, 0, 0.03],
                              opacity=0.9,
                              # rotation=180
                              )
            self._fig_pie_annotation_attributes = fig
        else:
            fig = self._fig_pie_annotation_attributes

        fig.update_layout(template=settings['theme'],
                          legend=dict(traceorder='normal',
                                      # ticks='inside',
                                      # tickvals=[0, 1, 2],
                                      # ticktext=attributes_value_counts.index,
                                      # dtick=3
                                      ),
                          legend_title_text='Attributes')

        return fig

    def sunburst_annotation_attribute_by_label(self, df, settings):
        if self._fig_sunburst_annotation_attribute_by_label is None:
            # 3, 2
            fig = px.sunburst(df.groupby(['label', 'attributes']).size().reset_index(name='Counts'),
                              path=['label', 'attributes'],
                              values='Counts',
                              color='attributes',  # Optional: use the counts as color

                              title='Annotation Attribute per Label')
            fig.update_traces(marker=dict(line=dict(color='#ffffff',
                                                    width=2)),
                              # pull=[0.05, 0, 0.03],
                              opacity=0.9)
            self._fig_sunburst_annotation_attribute_by_label = fig
        else:
            fig = self._fig_sunburst_annotation_attribute_by_label
        fig.update_layout(template=settings['theme'])

        return fig

    def heatmap_annotation_location(self, df, settings, max_item_width, max_item_height):
        if self._fig_heatmap_annotation_location is None:
            def add_single(wtop, wleft, wright, wbottom):
                try:
                    density_matrix[int(wtop):int(wbottom), int(wleft):int(wright)] += 1
                except Exception as e:
                    print(e)
                finally:
                    pbar.update()

            t = time.time()
            density_matrix = np.zeros((int(max_item_height), int(max_item_width)))
            # Populate the matrix based on bounding box locations
            pbar = tqdm.tqdm(total=df.shape[0])
            # pool = ThreadPoolExecutor(max_workers=32)
            for top, left, bottom, right in zip(df.top, df.left, df.bottom, df.right):
                density_matrix[int(top):int(bottom), int(left):int(right)] += 1
                # pool.submit(fn=add_single, wtop=top, wbottom=bottom, wleft=left, wright=right)
            print(f'density matrix creation time: {(time.time() - t):.2f}[s]')
            # pool.shutdown()
            fig = px.imshow(img=density_matrix,
                            title="Annotation Location Heatmap",
                            color_continuous_scale='Viridis',  # Colorscale
                            labels=dict(color="density"))
            self._fig_heatmap_annotation_location = fig
        else:
            fig = self._fig_heatmap_annotation_location
        fig.update_layout(coloraxis_reversescale=True,
                          template=settings['theme'])
        #
        # text=density_matrix,
        #                 hoverinfo="text",
        #                 colorbar=dict(
        #                     title="Surface Heat",
        #                     titleside="top",
        #                     tickmode="array",
        #                     tickvals=[2, 25, 50, 75, 100],
        #                     labelalias={100: "Hot", 50: "Mild", 2: "Cold"},
        #                     ticks="outside"
        #                 ),
        #                 showlegend=False,
        #                 colorscale='Viridis',  # Choose a colorscale
        #                 reversescale=True,  # Reverse color scale for visual preference
        #                 # colorbar=dict(title='Density')),  # Colorbar label
        #                 )
        # fig.update_layout(width=1200,
        #                   height=2000,
        #                   autosize=False,
        #                   showlegend=False,
        #                   coloraxis_showscale=False)
        return fig
        #

    def scatter_annotation_height_width(self, df, max_item_height, max_item_width, settings):
        if self._fig_scatter_annotation_height_width is None:
            a = df.groupby(['annotation_width', 'annotation_height']).size().reset_index(name='Counts')
            a['hover_text'] = [f'Count: {count}' for count in a['Counts']]
            fig = px.scatter(data_frame=a,
                             title="Annotation Height/Width",
                             x='annotation_height',
                             y='annotation_width',
                             size='Counts',
                             hover_name='hover_text',  # Set hover text
                             )
            fig.update_traces(marker=dict(sizemode='area', sizeref=2. * max(a['Counts']) / (40. ** 2), sizemin=1))
            fig.update_xaxes(range=[0, max_item_height],
                             title='Height')  # Set min x to 0 and max x to 40
            fig.update_yaxes(range=[0, max_item_width],
                             title='Width')  # Set min x to 0 and max x to 40
            self._fig_scatter_annotation_height_width = fig
        else:
            fig = self._fig_scatter_annotation_height_width
        fig.update_layout(template=settings['theme'])

        return fig

#
# if __name__ == "__main__":
#     dl.setenv('rc')
#     from main import Runner, Insights
#
#     dataset = dl.datasets.get(None, '5f4d13ba4a958a49a7747cd9')
#     insights = Insights()
#     df = insights.export_and_build_dataframe(dataset_id=dataset.id)
