import numpy as np
import time
import tqdm
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
def plot(self, df):
    # Create a subplot with 1 row and 2 columns
    fig = make_subplots(rows=4, cols=2, specs=[[{'type': 'xy'}, {'type': 'domain'}],
                                               [{'type': 'xy'}, {'type': 'xy'}],
                                               [{'type': 'domain'}, {'type': 'domain'}],
                                               [{'type': 'xy'}, {'type': 'xy'}]],
                        subplot_titles=(
                            "Number of Annotation/Item",
                            "Annotation Type Pie Chart",
                            "Labels Histogram",
                            "Item's Height vs Width",
                            "Attributes Pie Chart",
                            "Attributes by Label",
                            "Bounding Box Location Heatmap",
                            "Bounding Box Height vs Width"
                        ),
                        row_heights=[3, 3, 3, 3]
                        )
    # 1, 1

    group_counts = df.groupby('item_id').size().reset_index(name='counts')

    fig.add_trace(go.Histogram(x=group_counts.values[:, 1],
                               nbinsx=group_counts.values[:, 1].max()),
                  row=1,
                  col=1)
    fig.update_layout(xaxis1=dict(title='# Annotations'),
                      yaxis1=dict(title='# Items'))
    # 1, 2
    type_value_counts = df['type'].value_counts()

    fig.add_trace(go.Pie(labels=type_value_counts.index,
                         values=type_value_counts.values,
                         domain={'x': [0, 0.5]},
                         textinfo='none'),
                  row=1,
                  col=2)
    # 2, 1
    label_value_counts = df['label'].value_counts()
    fig.add_trace(go.Bar(x=label_value_counts.index,
                         y=label_value_counts.values,
                         ),
                  row=2,
                  col=1)

    # 2, 2
    a = df.groupby(['width', 'height']).size().reset_index(name='Counts')
    hover_text = [f'Count: {count}' for count in a['Counts']]
    # Create sunburst chart
    fig.add_trace(go.Scatter(x=a['height'],
                             y=a['width'],
                             x0=0,
                             y0=0,
                             mode='markers',
                             text=hover_text,  # Set hover text
                             hoverinfo='text+x+y',  # Customize hover info (show text, x, and y values)
                             marker=dict(
                                 size=a['Counts'],  # Use the counts for the size of the markers
                                 sizemode='area',  # This makes the size values represent area
                                 sizeref=2. * max(a['Counts']) / (40. ** 2),
                                 # Adjusts the scale of the marker sizes
                                 sizemin=4  # Minimum size of the markers
                             )
                             ),

                  row=2,
                  col=2)
    fig.update_layout(xaxis3=dict(range=[0, df['height'].max()],
                                  title='Height'),
                      yaxis3=dict(range=[0, df['width'].max()],
                                  title='Width'
                                  ))

    # 3, 1
    attributes_value_counts = df['attributes'].value_counts()

    fig.add_trace(go.Pie(labels=attributes_value_counts.index,
                         values=attributes_value_counts.values,
                         domain={'x': [0, 0.5]},
                         textinfo='none'),
                  row=3,
                  col=1)

    # 3, 2
    fig.add_trace(
        list(px.sunburst(df.groupby(['label', 'attributes']).size().reset_index(name='Counts'),
                         path=['label', 'attributes'],
                         values='Counts',
                         color='attributes',  # Optional: use the counts as color
                         title='Sunburst Chart').select_traces())[0],
        row=3,
        col=2
    )

    # 4, 1
    def add_single(wtop, wleft, wright, wbottom):
        try:
            density_matrix[int(wtop):int(wbottom), int(wleft):int(wright)] += 1
        except Exception as e:
            print(e)
        finally:
            pbar.update()

    t = time.time()
    density_matrix = np.zeros((int(df.height.max()), int(df.width.max())))
    # Populate the matrix based on bounding box locations
    pbar = tqdm.tqdm(total=df.shape[0])
    # pool = ThreadPoolExecutor(max_workers=32)
    for top, left, bottom, right in zip(df.top, df.left, df.bottom, df.right):
        density_matrix[int(top):int(bottom), int(left):int(right)] += 1
        # pool.submit(fn=add_single, wtop=top, wbottom=bottom, wleft=left, wright=right)
    print(f'density matrix creation time: {(time.time() - t):.2f}[s]')
    # pool.shutdown()
    fig.add_trace(go.Heatmap(z=density_matrix,
                             text=density_matrix,
                             hoverinfo="text",
                             colorbar=dict(
                                 title="Surface Heat",
                                 titleside="top",
                                 tickmode="array",
                                 tickvals=[2, 25, 50, 75, 100],
                                 labelalias={100: "Hot", 50: "Mild", 2: "Cold"},
                                 ticks="outside"
                             ),
                             showlegend=False,
                             colorscale='Viridis',  # Choose a colorscale
                             reversescale=True,  # Reverse color scale for visual preference
                             # colorbar=dict(title='Density')),  # Colorbar label
                             ),
                  row=4,
                  col=1)
    fig.update_layout(width=1200,
                      height=2000,
                      autosize=False,
                      showlegend=False,
                      coloraxis_showscale=False)

    # 4, 2
    a = df.groupby(['annotation_width', 'annotation_height']).size().reset_index(name='Counts')
    hover_text = [f'Count: {count}' for count in a['Counts']]
    # Create sunburst chart
    fig.add_trace(go.Scatter(x=a['annotation_height'],
                             y=a['annotation_width'],
                             x0=0,
                             y0=0,
                             mode='markers',
                             text=hover_text,  # Set hover text
                             hoverinfo='text+x+y',  # Customize hover info (show text, x, and y values)
                             marker=dict(
                                 size=a['Counts'],  # Use the counts for the size of the markers
                                 sizemode='area',  # This makes the size values represent area
                                 sizeref=2. * max(a['Counts']) / (40. ** 2),
                                 # Adjusts the scale of the marker sizes
                                 sizemin=4  # Minimum size of the markers
                             )
                             ),

                  row=4,
                  col=2)
    return fig