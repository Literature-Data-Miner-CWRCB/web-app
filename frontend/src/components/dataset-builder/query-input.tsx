// src/components/dataset-builder/query-input.tsx
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";

interface QueryInputProps {
	value: string;
	onChange: (value: string) => void;
}

export function QueryInput({ value, onChange }: QueryInputProps) {
	return (
		<Card className="mb-4">
			<CardContent className="pt-6">
				<div className="space-y-2">
					<Label htmlFor="search-query">
						Type what you are looking for
					</Label>
					<Input
						id="search-query"
						placeholder="E.g., neural networks for image classification"
						value={value}
						onChange={(e) => onChange(e.target.value)}
						className="w-full"
					/>
				</div>
			</CardContent>
		</Card>
	);
}
