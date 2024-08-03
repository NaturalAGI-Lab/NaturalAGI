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

## 2. Angle Points Detector

The `AnglePointsDetector` module is designed to handle the detection and calculation of angle points formed by the intersection of lines. This module includes functions to find the intersection points of lines, calculate the angles between intersecting lines, and generate angle points with unique identifiers. Below is a detailed description of the implementation of this module.

### Imports
The module imports the following libraries:
- `math`: Provides mathematical functions, including trigonometric functions.
- `uuid`: Generates unique identifiers for angle points.

### Functions

1. **line_intersection(line1, line2)**
   - This function calculates the intersection point of two lines, if it exists. The lines are represented as dictionaries with keys `'x1'`, `'y1'`, `'x2'`, and `'y2'` for the coordinates of their endpoints.
   - The function computes the intersection point using the formula for the intersection of two lines. If the lines are parallel (denominator is zero), it returns `None`.
   - A delta value is used to allow the intersection point to be up to 5 units outside the line bounds. The function checks if the intersection point lies within the extended boundaries of both lines and returns the intersection point as a list `[px, py]` if it does, otherwise it returns `None`.

2. **calculate_angle(line1, line2)**
   - This function calculates the angle between two intersecting lines. The lines are represented as dictionaries with keys `'x1'`, `'y1'`, `'x2'`, and `'y2'`.
   - The function computes the differences in the x and y coordinates for both lines and calculates the angles of the lines using the `atan2` function.
   - The absolute difference between the two angles is calculated, and if it exceeds π (180 degrees), it is adjusted to be the interior angle.
   - The angle is converted from radians to degrees and rounded to the nearest multiple of 5 using the `round_to_nearest` function.

3. **round_to_nearest(number, n)**
   - This helper function rounds a given number to the nearest multiple of `n`.

4. **calculate_angle_points(lines)**
   - This function calculates the angle points formed by the intersection of a list of lines. Each line is represented as a dictionary with keys `'x1'`, `'y1'`, `'x2'`, `'y2'`, and `'id'`.
   - The function iterates through all pairs of lines, calculates their intersection points using the `line_intersection` function, and if an intersection exists, calculates the angle between the lines using the `calculate_angle` function.
   - For each valid intersection, an angle point is created with a unique identifier (UUID), the coordinates of the intersection point, the calculated angle, and the identifiers of the intersecting lines.
   - The function returns a list of angle points.
  
### Usage
The `AnglePointsDetector` module is used to detect and calculate angle points formed by the intersection of lines in various applications, such as image analysis and computer vision. By using this module, one can efficiently find intersection points, calculate angles, and generate unique angle points for further analysis or processing.

## 3. Contour Analysis

The `contour_analysis` module is designed to analyze and process the structural elements of images, particularly focusing on lines and their intersections. This module is essential in computer vision tasks where understanding the geometric and topological properties of contours is crucial. Below is a detailed overview of the key components and their functionalities within the `contour_analysis` module.

### Key Components

1. **ContourAnalysisRepository**
   - This class manages the connection to the Neo4j database and orchestrates the contour analysis process. It initializes the database connection, processes input data, and triggers various analysis functions.
  
2. **Process Input Data**
   - This function processes the input data, which includes lines and angle points, and saves the relevant information to the database. It also handles the creation of critical points and the calculation of relative parameters.

3. **Angle Points Strategy**
   - This strategy class extracts and counts angle points for each image. It creates a new node named `AnglePointsCount` with the count as a property.

4. **Data Saver**
   - This module includes functions to save vector and intersection data to the database. It ensures that all relevant properties and relationships are correctly stored.

5. **Magnitude and Direction Service**
   - This service calculates the magnitude and direction of vectors and creates nodes to represent these properties. It also handles the creation of critical points when there is a change in direction.

6. **Unwinder**
   - The `Unwinder` class creates new angle points based on the `AnglePointCount` node and connects them with appropriate relationships.

7. **Exposition Analyzer**
   - This module analyzes the contour development for a given image, determining whether the development is monotonic or non-monotonic based on the directions of the vectors.

8. **Angle Point and Vector Models**
   - These models define the structure of angle points and vectors, including their properties and relationships.

9. **Tertiary Features Service**
   - This service executes various strategies to extract tertiary features from the contour data, such as angle points and quadrant changes.

10. **Graph Reduction Merger**
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