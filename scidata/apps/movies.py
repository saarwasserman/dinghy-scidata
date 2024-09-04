import csv
import json
from pathlib import Path
from typing import List

import click
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from opensearchpy.helpers import bulk
from openai import OpenAI

from scidata.config import settings
from scidata.openai.embeddings import create_embedding


# TODO: remove    embeddings_file = "/Users/saarw/Workspace/apps/dinghy/scidata/file-cdqEnf2j1ThjZmhxksw4Z0BC.jsonl"


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

  def create_index(self):
    """ """
    
    with OpenSearch(
      hosts = [settings.opensearch_host],
      http_auth = (settings.opensearch_username, settings.opensearch_password),
      use_ssl = True,
      verify_certs = True,
      connection_class = RequestsHttpConnection,  ## needs requests package installed
    ) as opensearch_client:
      createRes = opensearch_client.indices.create(index=OPENSEARCH_INDEX_NAME, body=MOVIES_INDEX)
      getRes = opensearch_client.indices.get(OPENSEARCH_INDEX_NAME)

    print(response)


  # get embeddings from batch results
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
          movies[result["custom_id"]]["Description_embed"] = result["response"]["body"]["data"][0]["embedding"]


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
      bulk(opensearch_client, documents)


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
    with OpenAI() as openai_client:
      response = openai_client.embeddings.create(
        input=description,
        model="text-embedding-3-small",
      )
      
      embedding = response.data[0].embedding
      
    return embedding


### CLI ###
  
@click.group(name="movies")
def cli_apps_movies():
    """movies embeddings app"""
    pass  # pylint: disable=unnecessary-pass


@cli_apps_movies.command(name="init")
@click.option("--documents_filepath", help="jsonl file to upload", required=True)
def init(documents_filepath):
  """ init the opensearch index and documents (include embeddings) """
  app = MoviesEmbeddingsApp()
  
  app.create_index()
  app.populate(documents_filepath)





@cli_apps_movies.command(name="search")
@click.option("--description", help="description of a movie", required=True)
def create_embedding_by_description(description: str) -> dict:
  app = MoviesEmbeddingsApp()
  app.create

@cli_apps_movies.command(name="search")
@click.option("--description", help="description of a movie", required=True)
@click.option("--amount", help="max number of movies you would like to see", default=3, required=True)
def search_by_description(description: str, amount: int) -> dict:
  """ get similar movies by description
      Args:
        description: some custom description related to movies you like
        amount: max results to retrieve
        
      Returns:
        a list of movies
  """
    
  embedding = create_embedding(description)
  
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
  
  results = opensearch_client.search(index="movies-index", body=body)
  print(results["hits"]["hits"])
