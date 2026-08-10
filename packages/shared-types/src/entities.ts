// Additional entity-specific types can be added here
export interface Relationship {
  from_entity_id: string | number;
  to_entity_id: string | number;
  relationship_type: string;
  confidence?: number;
  source?: string;
}
