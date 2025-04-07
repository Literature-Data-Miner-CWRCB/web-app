// src/components/dataset-builder/query-input.tsx
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

interface QueryInputProps {
	value: string;
	onChange: (value: string) => void;
}

export function QueryInput({ value, onChange }: QueryInputProps) {
	return (
		<div className="space-y-2">
			<Label htmlFor="search-query">Describe topic of interest</Label>
			<Textarea
				id="search-query"
				placeholder="E.g., neural networks for image classification"
				value={value}
				onChange={(e) => onChange(e.target.value)}
				className="min-h-[100px] w-full"
			/>
		</div>
	);
}
