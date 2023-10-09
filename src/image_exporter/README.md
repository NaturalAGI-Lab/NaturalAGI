# Image to tree

This component is aimed at exporting images to a graph DB, currently Neo4j

## Structure

- `image_to_neo_exporter.py` - consists of an implementation of the exporter for the Neo4j DB.
- `debugging_notebook.ipynd` - is the notebook for debugging purpose.
- `nuclio_handler.py` - consists of an implementation of a nuclio function that receives images via http requests and exports them into a graph db.
- `fucntion.yaml` - a nuclio function config.
- `Dockerfile` - a nuclio function docker file.