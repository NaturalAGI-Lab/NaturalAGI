// Classification hot path (image_id)
CREATE INDEX idx_point_image_id IF NOT EXISTS FOR (n:Point) ON (n.image_id);
CREATE INDEX idx_vector_image_id IF NOT EXISTS FOR (n:Vector) ON (n.image_id);

// Classification hot path (concept_id)
CREATE INDEX idx_point_concept_id IF NOT EXISTS FOR (n:Point) ON (n.concept_id);
CREATE INDEX idx_vector_concept_id IF NOT EXISTS FOR (n:Vector) ON (n.concept_id);

// Session queries (training, concept creation)
CREATE INDEX idx_point_session_id IF NOT EXISTS FOR (n:Point) ON (n.session_id);
CREATE INDEX idx_vector_session_id IF NOT EXISTS FOR (n:Vector) ON (n.session_id);

// StartPoint concept lookup
CREATE INDEX idx_startpoint_concept_id IF NOT EXISTS FOR (n:StartPoint) ON (n.concept_id);
