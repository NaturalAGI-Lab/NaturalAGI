# NaturalAGI

AGI research artifacts

## How to run the simulation

### Running a graph db

#### Docker command

```bash
docker run \
    --restart always \
    --publish=7474:7474 --publish=7687:7687 \
    --env NEO4J_AUTH=neo4j/your_password \ 
    --env NEO4J_PLUGINS='["graph-data-science"]' \
    neo4j:5.12.0
```

#### Docker compose command

Go to the folder `infrastructure`

```bash
docker compose up
```
