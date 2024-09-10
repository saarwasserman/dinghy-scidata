import csv
import json
from pathlib import Path
from typing import List

import click
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from opensearchpy.helpers import bulk
from openai import OpenAI

from scidata.config import settings


class MoviesEmbeddingsApp:
    # index to hold the movie documents. description_embed is the vector field.
    EMBEDDINGS_MODEL = "text-embedding-3-small"
    OPENSEARCH_INDEX_NAME = "movies-index"
    OPENSEARCH_INDEX_BODY = {
        "settings": {
            "index": {
                "knn": True,
                "knn.algo_param.ef_search": 100,
                "number_of_shards": 1,
                "number_of_replicas": 0
            }
        },
        "mappings": {
            "properties": {
                "description_embed": {
                    "type": "knn_vector",
                    "dimension": 1536,
                    "method": {
                        "name": "hnsw",
                        "space_type": "l2",
                        "engine": "lucene",
                        "parameters": {
                            "ef_construction": 100,
                            "m": 16
                        }
                    }
                }
            }
        }
    }

    def __init__(self):
        self.opensearch_client = None
        self.openai_client = None

    def __enter__(self):
        self.opensearch_client = OpenSearch(hosts=[settings.opensearch_host],
                                            http_auth=(
                                                settings.opensearch_username, settings.opensearch_password),
                                            use_ssl=True,
                                            verify_certs=True,
                                            # needs requests package installed)
                                            connection_class=RequestsHttpConnection,
                                            )

        self.openai_client = OpenAI()

        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.opensearch_client.close()
        self.openai_client.close()

    def create_index(self):
        """ """

        with OpenSearch(
            hosts=[settings.opensearch_host],
            http_auth=(settings.opensearch_username,
                       settings.opensearch_password),
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,  # needs requests package installed
        ) as opensearch_client:
            createRes = opensearch_client.indices.create(
                index=OPENSEARCH_INDEX_NAME, body=MOVIES_INDEX)
            getRes = opensearch_client.indices.get(OPENSEARCH_INDEX_NAME)

        print(response)

    def populate(self, documents_filepath, embeddings_filepath):
        movies = {}
        with open(documents_filepath, "r") as movies_file:
            # with open("/Users/saarw/Workspace/apps/dinghy/scidata/scidata/datasets/imdb/imdb.csv", "r") as movies_file:
            reader = csv.DictReader(movies_file, delimiter=",")
            for row in reader:
                movies[row["Rank"]] = row

            with open(embeddings_filepath, "r") as embed_file:
                for row in embed_file:
                    result = json.loads(row)
                    movies[result["custom_id"]
                           ]["Description_embed"] = result["response"]["body"]["data"][0]["embedding"]

        # create documents for bulk send to opensearch
        documents = []
        for movie in movies.values():
            documents.append({
                "_op_type": "index",
                "_index": "movies-index",
                "_id": movie["Rank"],
                "_source": {
                    "title": movie["Title"],
                    "genres": movie["Genre"],
                    "description": movie["Description"],
                    "description_embed": movie["Description_embed"]
                }
            })

        if documents:
            bulk(self.opensearch_client, documents)

    def create_batch_file(self, csv_filepath):
        """creates a .jsonl batch file of actions to upload to openai platform
        for embeddings retrieval

        Args:
            csv_file (str): csv to parse desired embedding for
        """
        requests = []
        with open(csv_file, "r") as movies_file:
            reader = csv.DictReader(movies_file, delimiter=",")
            for i, row in enumerate(reader):
                requests.append({
                    "custom_id": row["Rank"],
                    "method": "POST",
                    "url": "/v1/embeddings",
                    "body": {
                        "model": EMBEDDINGS_MODEL,
                        "input": row["Description"],
                    }
                })

        jsonl_out_filepath = f"{Path(csv_filepath).stem}.json"
        with open(jsonl_out_filepath, "w") as batch_file:
            batch_file.write('\n'.join(map(json.dumps, requests)))

        print(f"batch file is ready to be uploaded: {jsonl_out_filepath}")

    def create_movie_embedding(self, description: str) -> List[float] | None:
        """ retrieves an embedding for the movie description
          Args:
            description: movie description

          Returns:
            embedding of the description
        """

        embedding = None
        response = self.openai_client.embeddings.create(
            input=description,
            model="text-embedding-3-small",
        )

        embedding = response.data[0].embedding

        return embedding


### CLI ###

@click.group(name="movies")
@click.pass_context
def cli_apps_movies(ctx):
    """movies embeddings app"""
    ctx.obj = ctx.with_resource(MoviesEmbeddingsApp())


@cli_apps_movies.command(name="init")
@click.option("--documents_filepath", help="jsonl file to upload", required=True)
@click.pass_obj
def init(app: MoviesEmbeddingsApp, documents_filepath: str):
    """ init the opensearch index and documents (include embeddings) """
    app.create_index()
    app.populate(documents_filepath)


@cli_apps_movies.command(name="add")
@click.option("--movie_id", type=int, help="description of a movie", required=True)
@click.option("--title", type=str, help="description of a movie", required=True)
@click.option("--description", type=str, help="description of a movie", required=True)
@click.option("--genres", type=str, multiple=True, default=[], help="description of a movie", required=True)
@click.pass_obj
def add_movie(app: MoviesEmbeddingsApp, movie_id: int, title: str, description: str, genres: List[str]):
    """Add movie to DB"""

    embedding = app.create_movie_embedding(description)
    movie_document_body = {
        "title": title,
        "genres": genres,
        "description": description,
        "description_embed": embedding
    }

    app.opensearch_client.create(
        index=MoviesEmbeddingsApp.OPENSEARCH_INDEX_NAME, id=movie_id, body=movie_document_body)


@cli_apps_movies.command(name="search")
@click.option("--description", help="description of a movie", required=True)
@click.option("--amount", help="max number of movies you would like to see", default=3, required=True)
@click.pass_obj
def search_by_description(app: MoviesEmbeddingsApp, description: str, amount: int):
    """ get similar movies by description"""

    embedding = app.create_movie_embedding(description)
    body = {
        "size": amount,
        "_source": {
            "excludes": ["description_embed"],
        },
        "query": {
            "knn": {
                "description_embed": {
                    "vector": embedding,
                    "k": amount
                }
            }
        }
    }

    results = app.opensearch_client.search(index="movies-index", body=body)
    print(results["hits"]["hits"])
