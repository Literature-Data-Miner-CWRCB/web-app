// src/components/dataset-builder/OutputFormatSelector.tsx
import { Label } from "@/components/ui/label";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { OutputFormat } from "@/types/dataset";

interface OutputFormatSelectorProps {
	value: OutputFormat;
	onChange: (value: OutputFormat) => void;
}

export function OutputFormatSelector({
	value,
	onChange,
}: OutputFormatSelectorProps) {
	return (
		<div className="flex flex-col">
			<Label htmlFor="output-format" className="mb-2">
				Output Format
			</Label>
			<Select
				value={value}
				onValueChange={(val) => onChange(val as OutputFormat)}
			>
				<SelectTrigger id="output-format">
					<SelectValue placeholder="Select format" />
				</SelectTrigger>
				<SelectContent>
					<SelectItem value="csv">CSV</SelectItem>
					<SelectItem value="json">JSON</SelectItem>
				</SelectContent>
			</Select>
		</div>
	);
}
