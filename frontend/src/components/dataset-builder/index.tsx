// src/components/dataset-builder/index.tsx
"use client";
import { useState } from "react";
import { useDatasetBuilder } from "@/hooks/useDatasetBuilder";
import { useServerEvents } from "@/hooks/useServerEvents";
import { DataSchema } from "@/types/schema";
import { OutputFormat, FilterOption, DatasetQuery } from "@/types/dataset";
import { ProcessingStage } from "@/types/events";
import { QueryInput } from "./query-input";
import { FilterOptions } from "./filter-options";
import { OutputFormatSelector } from "./output-format-selecter";
import { SchemaDefinition } from "./schema-definition";
import { BuildButton } from "./build-button";
import { ProcessingIndicator } from "./processing-indicator";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { DatasetResults } from "@/components/results/dataset-results";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const filterOptions: FilterOption[] = [
	{ id: "peer-reviewed", name: "Peer-reviewed only" },
	{ id: "open-access", name: "Open access" },
	{ id: "recent", name: "Last 5 years" },
	{ id: "high-citations", name: "Highly cited" },
	{ id: "include-code", name: "Include code repositories" },
];

export function DatasetBuilder() {
	// Form state
	const [searchQuery, setSearchQuery] = useState("");
	const [selectedFilters, setSelectedFilters] = useState<string[]>([]);
	const [outputFormat, setOutputFormat] = useState<OutputFormat>("csv");
	const [rowLimit, setRowLimit] = useState(100);
	const [schema, setSchema] = useState<DataSchema>([]);

	// Validation state
	const isFormValid =
		searchQuery.trim() !== "" &&
		schema.length > 0 &&
		schema.every((field) => field.name.trim() !== "");

	// Processing state and hooks
	const { status, result, buildDataset } = useDatasetBuilder();
	const { startListening, stopListening } = useServerEvents();

	const handleBuild = () => {
		if (!isFormValid) return;

		const query: DatasetQuery = {
			searchQuery,
			filters: selectedFilters,
			outputFormat,
			rowLimit,
		};

		buildDataset(query, schema);
		startListening();
	};

	return (
		<div className="space-y-6">
			<div className="grid gap-6">
				<Card>
					<CardHeader>
						<CardTitle>Dataset Query</CardTitle>
					</CardHeader>
					<CardContent>
						<div className="grid gap-6">
							{/* Query input section */}
							<QueryInput
								value={searchQuery}
								onChange={setSearchQuery}
							/>

							{/* Selectors in responsive grid */}
							<div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
								<FilterOptions
									options={filterOptions}
									selectedFilters={selectedFilters}
									onFilterChange={setSelectedFilters}
								/>
								<OutputFormatSelector
									value={outputFormat}
									onChange={setOutputFormat}
								/>
								<div className="flex flex-col">
									<Label htmlFor="row-limit" className="mb-2">
										Rows ({rowLimit})
									</Label>
									<Slider
										id="row-limit"
										min={10}
										max={1000}
										step={10}
										value={[rowLimit]}
										onValueChange={(values) =>
											setRowLimit(values[0])
										}
									/>
								</div>
							</div>
						</div>
					</CardContent>
				</Card>

				<SchemaDefinition schema={schema} onSchemaChange={setSchema} />

				<ProcessingIndicator status={status} />

				<div className="flex justify-center">
					<BuildButton
						onClick={handleBuild}
						isLoading={
							status.stage !== ProcessingStage.IDLE &&
							status.stage !== ProcessingStage.COMPLETED &&
							status.stage !== ProcessingStage.ERROR
						}
						isDisabled={!isFormValid}
					/>
				</div>
			</div>

			{result && <DatasetResults result={result} />}
		</div>
	);
}
