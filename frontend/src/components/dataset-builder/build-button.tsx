// src/components/dataset-builder/BuildButton.tsx
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";

interface BuildButtonProps {
	onClick: () => void;
	isLoading: boolean;
	isDisabled: boolean;
}

export function BuildButton({
	onClick,
	isLoading,
	isDisabled,
}: BuildButtonProps) {
	return (
		<Button
			onClick={onClick}
			disabled={isLoading || isDisabled}
			size="lg"
			className="w-full md:w-auto"
		>
			{isLoading ? (
				<>
					<Loader2 className="mr-2 h-4 w-4 animate-spin" />{" "}
					Building...
				</>
			) : (
				"Build"
			)}
		</Button>
	);
}
