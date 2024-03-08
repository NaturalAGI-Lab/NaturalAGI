# NaturalAGI

AGI research artifacts

## How to run the simulation

### Running testing pipeline with all infrastructure

```bash
sh deploy_functions.sh
```

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

# Documentation

## Prefixes for features

There are list of prefixes in the system for different structures: 
- **AnglePoint** (intercestion point of 2 lines/vectors)
- **Vector** (line that has been truncated to the angle points)
- **Line** (result of line detector activation)
- **CriticalPoint** (point of the exposition that is critical for the recognized structure)

## Features

### Primary features

| Feature name    | Category    | Description                                                                                                                                                              |
| --------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Absolute        | Length      | Absolute value of the length of the structure in pixels                                                                                                                  |
| Magnitude       | Length      | The size of the vector                                                                                                                                                   |
| Angle           | Orientation | The direction of the structure is represented as an angle relative to a reference axis or plane                                                                          |
| Coordinates     | Location    | Coordinates of the structure. Might be (x, y) in case of a point and pair of coordinates [(x1, y1), (x2, y2)] in case of line/vector                                     |
| HalfPlane       | Location    | The half-plane in which the vector lies, determined by its orientation and position.                                                                                     |
| **Vector**Value | Location    | The numerical representation of the vector in terms of its components, particularly when the coordinate system is translated to the vector's starting point              |
| Quadrant        | Location    | The specific quadrant of the coordinate system in which the vector/line is located, particularly when the coordinate system is translated to the vector's starting point |

### Secondary features

| Feature name             | Category | Description                                                                                          |
| ------------------------ | -------- | ---------------------------------------------------------------------------------------------------- |
| **Vector**Direction      | Location | Determining whether a vector moves clockwise or counterclockwise                                     |
| **Vector**Comparison     | Location | Compares the magnitudes of vectors that intersect to assess their relative influence or significance |
| **Vector**QuadrantChange | Location | TODO add description                                                                                 |