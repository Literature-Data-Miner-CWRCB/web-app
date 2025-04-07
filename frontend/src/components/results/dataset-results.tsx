// src/components/results/dataset-results.tsx
import { useState } from "react";
import { DatasetResult } from "@/types/events";
import { ResultsTable } from "@/components/results/results-table";
import { TablePagination } from "@/components/results/table-pagination";
import { CitationDisplay } from "@/components/results/citation-display";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Download } from "lucide-react";

interface DatasetResultsProps {
	result: DatasetResult;
}

export function DatasetResults({ result }: DatasetResultsProps) {
	const [currentPage, setCurrentPage] = useState(1);
	const pageSize = 10;
	const totalPages = Math.ceil(result.data.length / pageSize);

	const handleDownload = (format: "csv" | "json") => {
		let content: string;
		let filename: string;

		if (format === "csv") {
			// Create CSV content
			const headers = result.schema.map((field) => field.name).join(",");
			const rows = result.data.map((row) =>
				result.schema
					.map((field) => {
						const value = row[field.name];
						if (typeof value === "string") {
							// Escape quotes and wrap in quotes
							return `"${value.replace(/"/g, '""')}"`;
						}
						return value !== null && value !== undefined
							? String(value)
							: "";
					})
					.join(",")
			);
			content = [headers, ...rows].join("\n");
			filename = "dataset.csv";
		} else {
			// Create JSON content
			content = JSON.stringify(result.data, null, 2);
			filename = "dataset.json";
		}

		// Create and trigger download
		const blob = new Blob([content], {
			type: format === "csv" ? "text/csv" : "application/json",
		});
		const url = URL.createObjectURL(blob);
		const link = document.createElement("a");
		link.href = url;
		link.download = filename;
		document.body.appendChild(link);
		link.click();
		document.body.removeChild(link);
		URL.revokeObjectURL(url);
	};

	return (
		<div className="my-8">
			<Card>
				<CardHeader className="flex flex-row items-center justify-between">
					<CardTitle>Results</CardTitle>
					<div className="flex gap-2">
						<Button
							variant="outline"
							size="sm"
							onClick={() => handleDownload("csv")}
						>
							<Download className="mr-2 h-4 w-4" /> CSV
						</Button>
						<Button
							variant="outline"
							size="sm"
							onClick={() => handleDownload("json")}
						>
							<Download className="mr-2 h-4 w-4" /> JSON
						</Button>
					</div>
				</CardHeader>
				<CardContent>
					<ResultsTable
						data={result.data}
						schema={result.schema}
						currentPage={currentPage}
						pageSize={pageSize}
					/>
					<TablePagination
						currentPage={currentPage}
						totalPages={totalPages}
						onPageChange={setCurrentPage}
					/>
				</CardContent>
			</Card>

			<CitationDisplay citations={result.citations} />
		</div>
	);
}
