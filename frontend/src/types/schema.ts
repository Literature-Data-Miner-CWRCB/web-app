// src/types/schema.ts
export type SchemaFieldType = 'str' | 'int' | 'float' | 'bool';

export interface SchemaField {
    name: string;
    type: SchemaFieldType;
    description: string;
}

export type DataSchema = SchemaField[];