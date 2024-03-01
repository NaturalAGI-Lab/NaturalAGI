# Dataset Generator

This component is aimed at generate a dataset of samples for training

## Structure

- `samples_generator.py` -  contains main functionality of generating shapes.
- `image_aggregator.py` - contains utility functions used by generator.

## Running

The generator has several options to make generated samples more complicated and noised in order to simulate more realistic shapes.
Parameters that can be specified:
- `--num_images` – number of images to generate;
- `--img_size` – images' resolutions in px;
- `--output_dir` – directory to save images. By default, ../../tests/generated_samples;
- `--is_noised` – flag to indicate if any other lines should appear on images;
- `--curved_sides` – flag to allow curved lines as triangles' sides;
- `--zigzag_sides` – flag to allow zigzag polygons as triangles' sides;

Example:

```bash        
python3 samples_generator.py --num_images 10 --img_size 512 --curved_sides True --zigzag_sides True
```
