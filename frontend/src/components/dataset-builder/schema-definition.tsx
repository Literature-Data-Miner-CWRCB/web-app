// src/components/dataset-builder/SchemaDefinition.tsx
import { Button } from "@/components/ui/button";
import {
	Table,
	TableBody,
	TableCell,
	TableHead,
	TableHeader,
	TableRow,
} from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DataSchema, SchemaField, SchemaFieldType } from "@/types/schema";
import { Plus, Trash2 } from "lucide-react";

interface SchemaDefinitionProps {
	schema: DataSchema;
	onSchemaChange: (schema: DataSchema) => void;
}

export function SchemaDefinition({
	schema,
	onSchemaChange,
}: SchemaDefinitionProps) {
	const fieldTypes: SchemaFieldType[] = [
		"string",
		"number",
		"boolean",
		"date",
		"array",
		"object",
	];

	const handleAddField = () => {
		onSchemaChange([
			...schema,
			{ name: "", type: "string", description: "" },
		]);
	};

	const handleRemoveField = (index: number) => {
		onSchemaChange(schema.filter((_, i) => i !== index));
	};

	const handleFieldChange = (index: number, field: string, value: string) => {
		const newSchema = [...schema];
		newSchema[index] = {
			...newSchema[index],
			[field]: field === "type" ? (value as SchemaFieldType) : value,
		};
		onSchemaChange(newSchema);
	};

	return (
		<Card className="my-6">
			<CardHeader>
				<CardTitle className="text-xl">
					Define your data schema
				</CardTitle>
			</CardHeader>
			<CardContent>
				<Table>
					<TableHeader>
						<TableRow>
							<TableHead>Name</TableHead>
							<TableHead>Type</TableHead>
							<TableHead>Description</TableHead>
							<TableHead className="w-[70px]"></TableHead>
						</TableRow>
					</TableHeader>
					<TableBody>
						{schema.map((field, index) => (
							<TableRow key={index}>
								<TableCell>
									<Input
										value={field.name}
										onChange={(e) =>
											handleFieldChange(
												index,
												"name",
												e.target.value
											)
										}
										placeholder="Field name"
									/>
								</TableCell>
								<TableCell>
									<Select
										value={field.type}
										onValueChange={(value) =>
											handleFieldChange(
												index,
												"type",
												value
											)
										}
									>
										<SelectTrigger>
											<SelectValue placeholder="Select type" />
										</SelectTrigger>
										<SelectContent>
											{fieldTypes.map((type) => (
												<SelectItem
													key={type}
													value={type}
												>
													{type}
												</SelectItem>
											))}
										</SelectContent>
									</Select>
								</TableCell>
								<TableCell>
									<Input
										value={field.description}
										onChange={(e) =>
											handleFieldChange(
												index,
												"description",
												e.target.value
											)
										}
										placeholder="Optional description"
									/>
								</TableCell>
								<TableCell>
									<Button
										variant="ghost"
										size="icon"
										onClick={() => handleRemoveField(index)}
									>
										<Trash2 className="h-4 w-4" />
									</Button>
								</TableCell>
							</TableRow>
						))}
						{schema.length === 0 && (
							<TableRow>
								<TableCell
									colSpan={4}
									className="h-24 text-center text-muted-foreground"
								>
									No fields defined yet. Add a field to get
									started.
								</TableCell>
							</TableRow>
						)}
					</TableBody>
				</Table>
				<Button
					onClick={handleAddField}
					variant="outline"
					size="sm"
				>
					<Plus className="mr-2 h-4 w-4" /> Add Field
				</Button>
			</CardContent>
		</Card>
	);
}
