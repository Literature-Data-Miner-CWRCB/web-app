// src/types/events.ts
import { DataSchema } from './schema';

export enum ProcessingStage {
    IDLE = 'idle',
    SEARCHING = 'searching',
    EXTRACTING = 'extracting',
    TRANSFORMING = 'transforming',
    VALIDATING = 'validating',
    COMPLETED = 'completed',
    ERROR = 'error'
}

export interface ProcessingStatus {
    stage: ProcessingStage;
    message: string;
    progress?: number;
}

export interface DatasetResult {
    id: string;
    data: any[];
    schema: DataSchema;
    totalRows: number;
    citations: Citation[];
}

export interface Citation {
    id: string;
    title: string;
    authors: string[];
    journal?: string;
    year: number;
    doi?: string;
    url?: string;
}