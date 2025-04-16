export type OutputFormat = 'csv' | 'json';


export type FilterOption = {
    id: string;
    name: string;
};

export interface DatasetQuery {
    searchQuery: string;
    filters: string[];
    outputFormat: OutputFormat;
    rowLimit: number;
}

// Define objects for the table generation

/**
 * Define the types of data stored in the columns
 */
export type ColumnFieldType = 'str' | 'int' | 'float' | 'bool';

/**
 * Reference to the source of the data
 */
export interface CitationModel {
    title: string;
    authors: string[];
    year: number;
    doi: string;
}

/**
 * A row in the table
 */
export interface RowModel {
    id?: string;
    fields: Record<string, any>;
    citations: CitationModel[];
}

export interface ColumnField {
    id?: string;
    name: string;
    type: ColumnFieldType;
    description: string; // could use as a tooltip when hovering over the column
}

export type ColumnFields = ColumnField[];
export type Rows = RowModel[];

export interface TableObject {
    id?: string;
    name: string;
    columns: ColumnFields;
    rows: Rows;
}

/**
 * Types for the progress of the dataset build
 */
export enum TaskStatus {
    PENDING = 'pending',
    STARTED = 'started',
    IN_PROGRESS = 'in_progress',
    COMPLETED = 'completed',
    FAILED = 'failed',
    REVOKED = 'revoked'
}

export interface TaskStatusUpdate {
    task_id: string;
    status: TaskStatus;
    message: string;
    result?: any; // Optional result data when task is completed
}