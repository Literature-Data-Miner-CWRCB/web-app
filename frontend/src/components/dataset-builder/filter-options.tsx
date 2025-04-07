// src/components/dataset-builder/filter-options.tsx
import { Button } from "@/components/ui/button";
import {
	DropdownMenu,
	DropdownMenuCheckboxItem,
	DropdownMenuContent,
	DropdownMenuLabel,
	DropdownMenuSeparator,
	DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { FilterOption } from "@/types/dataset";
import { ChevronDown } from "lucide-react";

interface FilterOptionsProps {
	options: FilterOption[];
	selectedFilters: string[];
	onFilterChange: (filters: string[]) => void;
}

export function FilterOptions({
	options,
	selectedFilters,
	onFilterChange,
}: FilterOptionsProps) {
	return (
		<div className="flex flex-col">
			<span className="mb-2 text-sm font-medium">Filter</span>
			<DropdownMenu>
				<DropdownMenuTrigger asChild>
					<Button
						variant="outline"
						className="w-full justify-between"
					>
						{selectedFilters.length > 0
							? `${selectedFilters.length} selected`
							: "Select filters"}
						<ChevronDown className="ml-2 h-4 w-4" />
					</Button>
				</DropdownMenuTrigger>
				<DropdownMenuContent className="w-56">
					<DropdownMenuLabel>Filter Options</DropdownMenuLabel>
					<DropdownMenuSeparator />
					{options.map((option) => (
						<DropdownMenuCheckboxItem
							key={option.id}
							checked={selectedFilters.includes(option.id)}
							onCheckedChange={(checked) => {
								if (checked) {
									onFilterChange([
										...selectedFilters,
										option.id,
									]);
								} else {
									onFilterChange(
										selectedFilters.filter(
											(id) => id !== option.id
										)
									);
								}
							}}
						>
							{option.name}
						</DropdownMenuCheckboxItem>
					))}
				</DropdownMenuContent>
			</DropdownMenu>
		</div>
	);
}
