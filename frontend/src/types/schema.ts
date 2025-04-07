// src/types/schema.ts
export type SchemaFieldType = 'string' | 'number' | 'boolean' | 'date' | 'array' | 'object';

export interface SchemaField {
    name: string;
    type: SchemaFieldType;
    description: string;
}

export type DataSchema = SchemaField[];