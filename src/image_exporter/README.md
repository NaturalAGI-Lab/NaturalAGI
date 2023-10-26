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

0. Configuration

The nuclio function is configured with env variables. Please configure env variables in the `docker-compose.yaml` accordingly

- `NEO4J_DSN=bolt://server1:7687` - neo4j uri
- `NEO4J_USER=neo4j` - neo4j username
- `NEO4J_PASS=111122223333` - neo4j password
- `NEXT_NUCLIO="func1;func2"` - list of next nuclio functions that should be called in the current function  

1. Neo4j and nthe nuclio dashboard components

    ```bash
        docker compose up

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

## Using nuctl tool

0. `nuctl` tool can be downloaded from the nuclio release page: <https://github.com/nuclio/nuclio/releases>

1. Deploying image_exporter using the nuctl tool:

    ```bash
        nuctl deploy --path . --platform local -e NEO4J_DSN=bolt://hostip:7687 -e NEO4J_USER=neo4j -e NEO4J_PASS=111122223333
    ```

2. Getting the list of deployed functions:

    ```bash
        nuctl get functions --platform local

        NAMESPACE | NAME           | PROJECT | STATE | REPLICAS | NODE PORT
        nuclio    | image-exporter | default | ready | 1/1      | 44807
    ```

3. Invoking image_exporter using the nuctl tool:

    ```bash
        nuctl invoke image-exporter --platform local --method POST --body '{"image": "Qk2uBAAAAAAAADYEAAAoAAAACgAAAAoAAAABAAgAAAAAAHgAAAAjLgAAIy4AAAABAAAAAQAAAAAAAAEBAQACAgIAAwMDAAQEBAAFBQUABgYGAAcHBwAICAgACQkJAAoKCgALCwsADAwMAA0NDQAODg4ADw8PABAQEAAREREAEhISABMTEwAUFBQAFRUVABYWFgAXFxcAGBgYABkZGQAaGhoAGxsbABwcHAAdHR0AHh4eAB8fHwAgICAAISEhACIiIgAjIyMAJCQkACUlJQAmJiYAJycnACgoKAApKSkAKioqACsrKwAsLCwALS0tAC4uLgAvLy8AMDAwADExMQAyMjIAMzMzADQ0NAA1NTUANjY2ADc3NwA4ODgAOTk5ADo6OgA7OzsAPDw8AD09PQA+Pj4APz8/AEBAQABBQUEAQkJCAENDQwBEREQARUVFAEZGRgBHR0cASEhIAElJSQBKSkoAS0tLAExMTABNTU0ATk5OAE9PTwBQUFAAUVFRAFJSUgBTU1MAVFRUAFVVVQBWVlYAV1dXAFhYWABZWVkAWlpaAFtbWwBcXFwAXV1dAF5eXgBfX18AYGBgAGFhYQBiYmIAY2NjAGRkZABlZWUAZmZmAGdnZwBoaGgAaWlpAGpqagBra2sAbGxsAG1tbQBubm4Ab29vAHBwcABxcXEAcnJyAHNzcwB0dHQAdXV1AHZ2dgB3d3cAeHh4AHl5eQB6enoAe3t7AHx8fAB9fX0Afn5+AH9/fwCAgIAAgYGBAIKCggCDg4MAhISEAIWFhQCGhoYAh4eHAIiIiACJiYkAioqKAIuLiwCMjIwAjY2NAI6OjgCPj48AkJCQAJGRkQCSkpIAk5OTAJSUlACVlZUAlpaWAJeXlwCYmJgAmZmZAJqamgCbm5sAnJycAJ2dnQCenp4An5+fAKCgoAChoaEAoqKiAKOjowCkpKQApaWlAKampgCnp6cAqKioAKmpqQCqqqoAq6urAKysrACtra0Arq6uAK+vrwCwsLAAsbGxALKysgCzs7MAtLS0ALW1tQC2trYAt7e3ALi4uAC5ubkAurq6ALu7uwC8vLwAvb29AL6+vgC/v78AwMDAAMHBwQDCwsIAw8PDAMTExADFxcUAxsbGAMfHxwDIyMgAycnJAMrKygDLy8sAzMzMAM3NzQDOzs4Az8/PANDQ0ADR0dEA0tLSANPT0wDU1NQA1dXVANbW1gDX19cA2NjYANnZ2QDa2toA29vbANzc3ADd3d0A3t7eAN/f3wDg4OAA4eHhAOLi4gDj4+MA5OTkAOXl5QDm5uYA5+fnAOjo6ADp6ekA6urqAOvr6wDs7OwA7e3tAO7u7gDv7+8A8PDwAPHx8QDy8vIA8/PzAPT09AD19fUA9vb2APf39wD4+PgA+fn5APr6+gD7+/sA/Pz8AP39/QD+/v4A////AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAP////////////8AAP////////////8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=="}' --content-type "application/json"
    ```

4. Delete a nuclio function:

    ```bash
        nuctl delete fu image-exporter --platform local

        23.10.27 00:05:19.652 (I)            nuctl.platform Successfully deleted function {"name": "image-exporter"}
    ```
