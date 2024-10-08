# Natural AGI description

## Table of Contents

1. [Features](./FEATURES.md)
2. [Pre-detectors](#pre-detectors)
   1. [Line Detector](#1-line-detector)

## 1. Line Detector
For lines detection we use Hough Transform function from OpenCV library. It is a standard function for this kind of task. To approximate all "noise" we use minLineLength and maxLineGap parameters along with the HoughBuilder class.

### Details of HoughBundler class

The `HoughBundler` class is designed to process and merge line segments detected in images using the Hough Transform. This class is particularly useful in computer vision tasks where line detection and grouping are essential, such as in the analysis of structural elements in images. Below is a detailed description of the implementation of the `HoughBundler` class.

#### Initialization

The class is initialized with two parameters:

- `min_distance`: The minimum distance between lines to consider them as separate entities.
- `min_angle`: The minimum angle difference between lines to consider them as separate entities.
These parameters help in determining whether two lines should be grouped together or treated as distinct lines

#### Methods

1. **get_orientation(line)**
   - This method calculates the orientation of a given line segment. The orientation is computed using the arctangent of the absolute differences in the y-coordinates and x-coordinates of the line's endpoints. The result is then converted from radians to degrees.
2. **check_is_line_different(line_1, groups, min_distance_to_merge, min_angle_to_merge)**
   - This method checks if a given line (`line_1`) is different from the lines in existing groups. It iterates through each group and each line within the group to compare distances and orientations. If the distance between `line_1` and any line in the group is less than `min_distance_to_merge` and the orientation difference is less than `min_angle_to_merge`, `line_1` is added to the group. Otherwise, it is considered a different line.
3. **distance_point_to_line(point, line)**
   - This method calculates the distance from a point to a line segment. It uses the formula for the distance from a point to a line and handles cases where the closest point on the line segment is one of the endpoints.
4. **get_distance(a_line, b_line)**
   - This method calculates the minimum distance between two line segments. It computes the distances from the endpoints of one line to the other line and returns the smallest distance.
5. **merge_lines_into_groups(lines)**
   - This method groups similar lines together. It starts by creating a new group for the first line and then iterates through the remaining lines. For each new line, it checks if it is different from the existing groups using the `check_is_line_different` method. If it is different, a new group is created for it.
6. **merge_line_segments(lines)**
   - This method merges line segments within a group into a single line segment. It calculates the orientation of the first line in the group and sorts the endpoints of all lines in the group based on their x or y coordinates, depending on the orientation. The merged line segment is created from the first and last points in the sorted list.
7. **process_lines(lines)**
   - This method processes the detected lines by separating them into horizontal and vertical lines based on their orientation. It then sorts and groups the lines, merging each group into a single line segment. The result is a list of merged line segments.


#### Usage

The `HoughBundler` class is used to refine the output of the Hough Transform by grouping and merging line segments that are close to each other and have similar orientations. This is particularly useful in applications such as image analysis, where detecting and processing structural elements like lines is crucial.

## 2. Contour Analysis

The `contour_analysis` module is designed to analyze and process the structural elements of images, particularly focusing on lines and their intersections. This module is essential in computer vision tasks where understanding the geometric and topological properties of contours is crucial. Below is a detailed overview of the key components and their functionalities within the `contour_analysis` module.

### Key Components

1. **ContourAnalysisRepository**
   - This class manages the connection to the Neo4j database and orchestrates the contour analysis process. It initializes the database connection, processes input data, and triggers various analysis functions.
  
2. **Process Input Data**
   - This function processes the input data, which includes lines and angle points, and saves the relevant information to the database. It also handles the creation of critical points and the calculation of relative parameters.

3. **Data Saver**
   - This module includes functions to save vector and intersection data to the database. It ensures that all relevant properties and relationships are correctly stored.

4. **Magnitude and Direction Service**
   - This service calculates the magnitude and direction of vectors and creates nodes to represent these properties. It also handles the creation of critical points when there is a change in direction.

5. **Exposition Analyzer**
   - This module analyzes the contour development for a given image, determining whether the development is monotonic or non-monotonic based on the directions of the vectors.

6. **Angle Point and Vector Models**
   - These models define the structure of angle points and vectors, including their properties and relationships.

7. **Tertiary Features Service**
   - This service executes various strategies to extract tertiary features from the contour data, such as angle points and quadrant changes.

8.  **Graph Reduction Merger**
    - This module merges graphs of structural elements in the database by grouping similar elements and comparing their properties using Levenshtein distance.

### Usage
The `contour_analysis` module is used to analyze the structural elements of images, focusing on lines and their intersections. By processing input data, saving relevant properties, and analyzing the geometric relationships, this module provides a comprehensive understanding of the contours in an image. This is particularly useful in applications such as image analysis, computer vision, and pattern recognition, where accurate detection and analysis of structural elements are crucial.

## Experiments and Results

### Low number of images

The first experiment was to test the system with 10 images and analyze how they form the concept.

To form the concept system should extract only stable structures and features.
**Stable structures and features** are the ones that are present in all images.

The first experiment was with 12 images with triangle on them. There were no either other objects or "noise" on the images.

As a result we've got the concept with following features:
- 3 angle points
- Closed contour
- 3rd quadrant
- Lower Half Plane
- Left Half Plane

![12 images concept image](12_images_concept.png)


### High number of images

The second experiment was with the 117 images. There were no either other objects or "noise" on the images.

As a result we've got the concept with following features:
- 3 angle points
- Closed contour
- Left Half Plane

![117 images concept image](117_images_concept.png)

### Results

As an outcome we can be sure that size of the training set matters for the concept formation.