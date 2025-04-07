// src/types/dataset.ts
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