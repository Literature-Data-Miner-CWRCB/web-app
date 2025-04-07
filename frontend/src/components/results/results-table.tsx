// src/components/results/ResultsTable.tsx
import {
	Table,
	TableBody,
	TableCell,
	TableHead,
	TableHeader,
	TableRow,
} from "@/components/ui/table";
import { DataSchema } from "@/types/schema";

interface ResultsTableProps {
	data: any[];
	schema: DataSchema;
	currentPage: number;
	pageSize: number;
}

export function ResultsTable({
	data,
	schema,
	currentPage,
	pageSize,
}: ResultsTableProps) {
	const startIndex = (currentPage - 1) * pageSize;
	const paginatedData = data.slice(startIndex, startIndex + pageSize);

	const formatCellValue = (value: any, type: string) => {
		if (value === null || value === undefined) {
			return "-";
		}

		switch (type) {
			case "date":
				return new Date(value).toLocaleDateString();
			case "boolean":
				return value ? "Yes" : "No";
			case "object":
			case "array":
				return JSON.stringify(value);
			default:
				return String(value);
		}
	};

	return (
		<div className="rounded-md border">
			<Table>
				<TableHeader>
					<TableRow>
						{schema.map((field) => (
							<TableHead key={field.name}>{field.name}</TableHead>
						))}
					</TableRow>
				</TableHeader>
				<TableBody>
					{paginatedData.length > 0 ? (
						paginatedData.map((row, rowIndex) => (
							<TableRow key={rowIndex}>
								{schema.map((field) => (
									<TableCell key={field.name}>
										{formatCellValue(
											row[field.name],
											field.type
										)}
									</TableCell>
								))}
							</TableRow>
						))
					) : (
						<TableRow>
							<TableCell
								colSpan={schema.length}
								className="h-24 text-center"
							>
								No results.
							</TableCell>
						</TableRow>
					)}
				</TableBody>
			</Table>
		</div>
	);
}
