# Image to tree

This component is aimed at exporting images to a graph DB, currently Neo4j

## Structure

- `image_to_neo_exporter.py` - consists of an implementation of the exporter for the Neo4j DB.
- `debugging_notebook.ipynd` - is the notebook for debugging purpose.
- `nuclio_handler.py` - consists of an implementation of a nuclio function that receives images via http requests and exports them into a graph db.
- `fucntion.yaml` - a nuclio function config.
- `Dockerfile` - a nuclio function docker file.

## Building

```bash
cd src/image_exporter
docker build -t image-exporter .
```

## Running

1. All components

    ```bash
        docker compose up

    ```

2. Only the image exporter

    ```bash
        docker compose up image-exporter
    ```

## Sending images

```bash
image=$(cat /home/DATA/Projects/science/NaturalAGI/tests/test-data/test-image.bmp | base64 | tr -d '\n')
```

```bash
cat << EOF > /tmp/input.json
{"image": "$image"}
EOF
```

```bash
curl -H "Content-Type: application/json" --data @/tmp/input.json http://localhost:8080
```
