// src/types/events.ts
import { DataSchema } from './schema';

export enum TaskStatus {
    IDLE = 'idle',
    STARTED = 'started',
    PROGRESS = 'progress',
    SUCCESS = 'success',
    FAILURE = 'failure',
    REVOKED = 'revoked'
}

export interface TaskStage {
    name: string;
    description: string;
    startedAt: Date;
    completedAt: Date;
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