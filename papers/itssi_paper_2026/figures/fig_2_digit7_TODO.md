# Figure 2 — Graph representation of a digit "7" image (TODO)

**Чому TODO:** для побудови потрібно (а) обрати конкретне зображення «7» з `datasets/mnist_all/7/`, що успішно класифікувалося; (б) запустити сервіси `skeletonization` + `contour_analysis` на ньому, щоб дістати з Neo4j вузли Point/Vector; (в) намалювати накладений граф поверх растру. Це окремий мікро-пайплайн, який зручніше виконати в Jupyter-нотбуці після Neo4j-запиту, а не в межах підготовки артефактів.

## Що має зображувати

Двопанельний рисунок:
- **Зліва:** оригінальне зображення цифри «7» зі стандартного MNIST (зразок із підмножини `structure=complete`), 100×100, у відтінках сірого. Підпис: «Вхідне зображення».
- **Справа:** той самий растр у блідо-сірому як підкладка, поверх якого накладено бінарний граф Point/Vector:
  - вузли `Point` — невеликі чорні кружечки;
  - вузли `Vector` — короткі стрілки уздовж відповідних ребер скелета;
  - ребра типу `CONNECTED_TO` між Point-вузлами — суцільні лінії;
  - підписи координат `(x, y)` біля 2—3 ключових вузлів (по одному endpoint, junction, corner) — як приклад збережених ознак.

## Як отримати дані для рисунка (рецепт)

```python
# 1. Обрати зображення
image_path = "datasets/mnist_all/7/<some-image-from-incorrect_results-correct=True>.png"

# 2. Подати на конектор:
#    curl -X POST -F "image=@${image_path}" http://localhost:5002/classify
# 3. Знайти session_id з відповіді (image_id повертається в JSON)
# 4. У Neo4j (bolt://localhost:7687, neo4j/111122223333) виконати:
#    MATCH (p:Point {image_id: $image_id})
#    OPTIONAL MATCH (p)-[r:CONNECTED_TO]-(p2:Point {image_id: $image_id})
#    OPTIONAL MATCH (p)-[:HAS_VECTOR]->(v:Vector {image_id: $image_id})
#    RETURN p.normalized_x, p.normalized_y, p.is_endpoint, p.is_corner,
#           collect(distinct {x: p2.normalized_x, y: p2.normalized_y}) AS neighbors,
#           collect(distinct {x: v.normalized_x, y: v.normalized_y}) AS vectors
# 5. Денормалізувати координати множенням на 100, накласти на оригінальне зображення matplotlib-ом
```

## Підпис до рисунка (для статті)

> Рис. 2. Графове представлення цифри «7». Зліва: вхідне бінарне зображення 100×100 з підмножини `structure=complete` MNIST. Справа: бінарний граф Point/Vector після етапів скелетонізації (GNG) та контурного аналізу — невеликі кружечки позначають вузли Point (геометричні точки контуру), стрілки — вузли Vector (короткі ребра з напрямком), суцільні лінії — ребра CONNECTED_TO. Біля кількох ключових вузлів показано збережені ознаки `(x, y, is_endpoint, is_corner)`.

## Розмір PNG

≥ 2 400 px по ширині, dpi=300, формат `.png`. Файл: `fig_2_digit7_graph.png`.
