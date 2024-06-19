import os
import json
from dotenv import load_dotenv
import networkx as nx
import matplotlib.pyplot as plt
from bokeh.io import show
from bokeh.plotting import figure, from_networkx
from bokeh.models import ColumnDataSource, Label, LabelSet, WheelZoomTool, PanTool, ResetTool, SaveTool


class RenderWikiGraph:
    SIZE_STEP = 3

    def __init__(self, data: list[dict[str, list[str]]]) -> None:
        self.titles = dict()
        for item in data:
            if not self.titles:
                self.titles[item['title']] = {
                    'size': self.SIZE_STEP,
                    'references': []
                }
            for ref in item['references']:
                if ref in self.titles:
                    self.titles[ref]['size'] += self.SIZE_STEP
                else:
                    self.titles[ref] = {
                        'size': 2 * self.SIZE_STEP,
                        'references': []
                    }
                self.titles[item['title']]['references'].append(ref)


if __name__ == "__main__":
    data_exists = False
    if os.path.isfile('.env'):
        load_dotenv('.env')
        graph_file = os.getenv('GRAPH_FILE')
        if os.path.isfile(graph_file):
            with open(graph_file, 'r') as f:
                json_data = json.load(f)
            graph_data = RenderWikiGraph(json_data)
            print('Database loaded.')
            data_exists = True

    if data_exists:

        G = nx.DiGraph()
        node_data = {'name': [], 'size': [], 'x': [], 'y': []}
        for title, data in graph_data.titles.items():
            G.add_node(title)
            node_data['name'].append(title)
            for reference in data['references']:
                G.add_edge(title, reference)

        pos = nx.spectral_layout(G, scale=100)
        for title, coordinates in pos.items():
            node_data['x'].append(coordinates[0])
            node_data['y'].append(coordinates[1])
            node_data['size'].append(graph_data.titles[title]['size'])

        print('edges: ', len(G.edges), 'nodes: ', len(G.nodes))

        nx.draw(G,
                pos,
                with_labels=False,
                node_size=[
                    data['size'] * 25 for data in graph_data.titles.values()
                ],
                arrowsize=0.005)
        for i, (node, (x, y)) in enumerate(pos.items()):
            plt.text(x,
                     y,
                     node,
                     fontsize=node_data['size'][i],
                     ha='center',
                     va='center')
        plt.savefig("wiki_graph.png", dpi=300, bbox_inches='tight')
        print('File saved as wiki_graph.png.')

        plot = figure(
            title="Interactive Wiki Graph",
            width=1200,
            height=800,
            x_range=(-101, 101),
            y_range=(-101, 101),
            tools=[PanTool(),
                   WheelZoomTool(),
                   ResetTool(),
                   SaveTool()])
        plot.toolbar.active_scroll = plot.select_one(WheelZoomTool)
        plot.axis.visible = False
        plot.grid.visible = False

        graph_renderer = from_networkx(G, pos, center=(0, 0))
        graph_renderer.edge_renderer.glyph.line_alpha = 0.06
        plot.renderers.append(graph_renderer)

        data_source = ColumnDataSource(data=node_data)
        labels = LabelSet(x="x", y="y", text="index", source=data_source)
        for i, fsize in enumerate(data_source.data['size']):
            label = Label(x=data_source.data['x'][i],
                          y=data_source.data['y'][i],
                          text=data_source.data['name'][i],
                          text_font_size=str(fsize) + "pt",
                          x_offset=0,
                          y_offset=0)
            plot.add_layout(label)
        plot.scatter(x='x',
                     y='y',
                     size='size',
                     source=data_source,
                     name="circles")

        show(plot)

    else:
        print("Database not found. Please, run 'python3 cache_wiki.py'")
