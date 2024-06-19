from pynput import keyboard
from bs4 import BeautifulSoup, Tag
import requests
import argparse
import logging
import json
import os
import concurrent.futures
from neo4j import GraphDatabase
from dotenv import load_dotenv


class WikiGraph:
    BAD_IDS = [
        'References', 'catlinks', 'External_links', 'Notes', 'Footnotes',
        'Citations'
    ]
    BAD_STRINGS = [
        'cite_note', 'Citation_needed', 'NOTRS', 'https', '(disambiguation)',
        ':', 'action='
    ]

    def __init__(self, title: str) -> None:
        self.data = []
        self.titles = set()
        self.current_unparsed = [title]
        self.future_unparsed = []

    def __len__(self) -> int:
        return len(self.titles)

    def unparsed(self) -> list[str]:
        return self.current_unparsed

    def unparsed_update(self) -> None:
        self.current_unparsed, self.future_unparsed = self.future_unparsed, []

    @staticmethod
    def get_wiki_url(title: str) -> str:
        return f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"

    def parse(self, title: str) -> bool:
        if title in self.titles:
            return False  # Статья уже была обработана

        html_content = BeautifulSoup(
            requests.get(self.get_wiki_url(title)).content, "html.parser")
        if html_content.select_one('.noarticletext'):
            return False  # Статья не существует или пустая

        index = len(self.titles)
        self.titles.add(title)
        self.data.append({'title': title, 'references': []})
        for element in html_content.select_one(
                '.mw-content-ltr').next_elements:
            if isinstance(element,
                          Tag) and element.name == 'a' and element.get('href'):
                if element.get('id') in self.BAD_IDS:
                    break
                href = element.get('href')
                if '/wiki' in href and not any(
                        bad_string in href for bad_string in self.BAD_STRINGS):
                    ref = element.get('title')
                    if ref not in self.data[index]['references']:
                        self.data[index]['references'].append(ref)
                        if ref not in self.titles:
                            self.future_unparsed.append(ref)
        return True


def on_key_press(key: keyboard.Key) -> None:
    global exit_flag
    if key == keyboard.Key.esc:
        exit_flag = True


def process_ref(ref: str) -> None:
    if wiki_cache.parse(ref):
        logger.info(
            f'{len(wiki_cache):4d}: Completed parsing of the article "{ref}"')


if __name__ == "__main__":
    os.environ["GRAPH_FILE"] = 'wiki.json'
    exit_flag = False

    start_params = argparse.ArgumentParser(
        description="Parses Wikipedia and saves internal links in json")
    start_params.add_argument('-d',
                              '--depth',
                              type=int,
                              default=3,
                              help="The parsing depth")
    start_params.add_argument('-p',
                              '--page',
                              default='Welsh Corgi',
                              type=str,
                              help="The starting article")
    start_params.add_argument(
        '-n',
        '--neo4j',
        action='store_true',
        help="If selected, it will load links into the neo4j database")
    start_params.add_argument('-m',
                              '--max',
                              type=int,
                              default=1000,
                              help="The maximum number of articles")
    args = start_params.parse_args()

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('wiki_logger')

    thread_number = 6
    max_depth = args.depth + 1
    if max_depth <= 1:
        start_params.error("The depth value must be greater than 0")
    max_articles = args.max - thread_number - 1
    if max_articles <= 0:
        start_params.error(
            f"The maximum number of articles must be greater than {thread_number + 1}"
        )
    wiki_cache = WikiGraph(args.page)
    print("You can press 'esc' to stop the parsing.")
    keyboard.Listener(on_press=on_key_press).start()

    for depth in range(max_depth):
        print(f'------------------------- {depth} -------------------------')
        with concurrent.futures.ThreadPoolExecutor(
                max_workers=thread_number) as executor:
            future_to_ref = {
                executor.submit(process_ref, ref): ref
                for ref in wiki_cache.unparsed()
            }
            for future in concurrent.futures.as_completed(future_to_ref):
                if len(wiki_cache) > max_articles or exit_flag:
                    exit_flag = True
                    break
            executor.shutdown(cancel_futures=True)
            wiki_cache.unparsed_update()
            if exit_flag or len(wiki_cache) == 0:
                break
    keyboard.Listener(on_press=on_key_press).stop()

    if len(wiki_cache) == 0:
        print(
            'This article does not exist. Please, choose some other default starting page.'
        )
    elif len(wiki_cache) < 20:
        if exit_flag:
            print(
                'Not enough articles. Please, try restarting and waiting for a while longer.'
            )
        else:
            print(
                'Not enough articles. Please, choose some other default starting page.'
            )
    else:
        with open(os.environ["GRAPH_FILE"], 'w',
                  encoding='utf-8') as json_file:
            json.dump(wiki_cache.data, json_file, ensure_ascii=False, indent=2)
        with open('.env', 'w') as f:
            f.write('GRAPH_FILE=' + os.environ["GRAPH_FILE"])

    if start_params.parse_args().neo4j:
        load_dotenv('neo4j_env/.env')
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USER")
        password = os.getenv("NEO4J_PASSWORD")
        driver = GraphDatabase.driver(uri, auth=(user, password))

        with driver.session() as session:
            session.run("MERGE (t:Title {name: $title})",
                        title=wiki_cache.data[0]['title'])
            for titles in wiki_cache.data:
                ref_list = titles['references']
                chunk_size = 30
                for i in range(0, len(ref_list), chunk_size):
                    chunk = ref_list[i:i + chunk_size]
                    merge_statements = " ".join([
                        f"MERGE (r{j}:Title {{name: $ref_title{j}}})"
                        for j in range(len(chunk))
                    ])
                    create_statements = " ".join([
                        f"CREATE (t)-[:REFERS_TO]->(r{k})"
                        for k in range(len(chunk))
                    ])
                    query = ("MATCH (t:Title {name: $title}) " +
                             merge_statements + create_statements)
                    parameters = {"title": titles['title']}
                    parameters.update({
                        f"ref_title{l}": ref_list[i + l]
                        for l in range(len(chunk))
                    })
                    session.run(query, parameters)
        driver.close()
