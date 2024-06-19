import os
import argparse
import json
from queue import Queue
from dotenv import load_dotenv
from typing import Optional


class GraphFromWiki:

    def __init__(self, data: list[str], non_directed: bool) -> None:
        self.vertices = set()
        self.edges = set()
        for item in data:
            self.vertices.add(item['title'])
            for ref in item['references']:
                self.vertices.add(ref)
                self.edges.add((item['title'], ref))
                if non_directed:
                    self.edges.add((ref, item['title']))

    def neighbors(self, vertex: str) -> list[str]:
        return [edge[1] for edge in self.edges if edge[0] == vertex]

    def bfs(self, start: str, end: str) -> Optional[int]:
        current_level_queue = Queue()
        current_level_queue.put(start)
        next_level_queue = Queue()
        visited = set()
        level = 0
        while not current_level_queue.empty():
            vertex = current_level_queue.get()
            if vertex == end:
                return level
            if vertex not in visited:
                visited.add(vertex)
                for neighbor in self.neighbors(vertex):
                    next_level_queue.put(neighbor)
            if current_level_queue.empty():
                current_level_queue, next_level_queue = next_level_queue, current_level_queue
                level += 1
        return None

    def bfs_with_path(self, start: str, end: str) -> Optional[list[str]]:
        queue = Queue()
        queue.put((start, [start]))
        visited = set()
        while not queue.empty():
            vertex, path = queue.get()
            if vertex == end:
                return path
            visited.add(vertex)
            for neighbor in self.neighbors(vertex):
                if neighbor not in visited:
                    queue.put((neighbor, path + [neighbor]))
        return None

    def shortest_path(self, start: str, end: str, view_path: bool,
                      non_directed: bool) -> Optional[str]:
        if start not in self.vertices or end not in self.vertices:
            return None
        if view_path:
            result = ''
            path = self.bfs_with_path(start, end)
            if path:
                link_char = ' -- ' if non_directed else ' -> '
                for i in range(len(path) - 1):
                    result += path[i] + link_char
                result += path[-1] + '\n' + str(len(path) - 1)
                return result
            else:
                return 'Path not found'
        else:
            result = self.bfs(start, end)
            return result if result else 'Path not found'


if __name__ == "__main__":
    start_params = argparse.ArgumentParser(
        description=
        "Finds the shortest distance between two Wikipedia articles from a json file"
    )
    start_params.add_argument('--from',
                              type=str,
                              default='Welsh Corgi',
                              help="The starting article")
    start_params.add_argument('--to',
                              type=str,
                              default='Python (programming language)',
                              help="The final article")
    start_params.add_argument(
        '--non-directed',
        action='store_true',
        help="If it is selected, links are considered bidirectional")
    start_params.add_argument('-v',
                              action='store_true',
                              help="If it is selected, the path is displayed")
    args = start_params.parse_args()
    data_exists = False

    if os.path.isfile('.env'):
        load_dotenv('.env')
        graph_file = os.getenv('GRAPH_FILE')
        if os.path.isfile(graph_file):
            data_exists = True
            with open(graph_file, 'r') as f:
                json_data = json.load(f)

    if data_exists:
        graph = GraphFromWiki(json_data, args.non_directed)
        path = graph.shortest_path(getattr(args, 'from'), getattr(args, 'to'),
                                   getattr(args, 'v'),
                                   getattr(args, 'non_directed'))
        if path is not None:
            print(path)
        else:
            print("Title not found in database")
    else:
        print("Database not found. Please, run 'python3 cache_wiki.py")
