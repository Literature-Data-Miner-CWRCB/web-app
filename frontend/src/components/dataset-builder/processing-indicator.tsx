// src/components/dataset-builder/ProcessingIndicator.tsx
import { Progress } from "@/components/ui/progress";
import { Card, CardContent } from "@/components/ui/card";
import { ProcessingStage, ProcessingStatus } from "@/types/events";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { CheckCircle, AlertTriangle, Loader2 } from "lucide-react";
import { cva } from "class-variance-authority";

interface ProcessingIndicatorProps {
	status: ProcessingStatus;
}

const stageIcons = {
	[ProcessingStage.IDLE]: null,
	[ProcessingStage.SEARCHING]: <Loader2 className="h-4 w-4 animate-spin" />,
	[ProcessingStage.EXTRACTING]: <Loader2 className="h-4 w-4 animate-spin" />,
	[ProcessingStage.TRANSFORMING]: (
		<Loader2 className="h-4 w-4 animate-spin" />
	),
	[ProcessingStage.VALIDATING]: <Loader2 className="h-4 w-4 animate-spin" />,
	[ProcessingStage.COMPLETED]: (
		<CheckCircle className="h-4 w-4 text-green-500" />
	),
	[ProcessingStage.ERROR]: <AlertTriangle className="h-4 w-4 text-red-500" />,
};

const alertVariant = cva("", {
	variants: {
		stage: {
			[ProcessingStage.IDLE]: "",
			[ProcessingStage.ERROR]: "border-red-500 text-red-500",
			[ProcessingStage.COMPLETED]: "border-green-500 text-green-500",
			default: "border-blue-500 text-blue-500",
		},
	},
	defaultVariants: {
		stage: "default",
	},
});

export function ProcessingIndicator({ status }: ProcessingIndicatorProps) {
	if (status.stage === ProcessingStage.IDLE) {
		return null;
	}

	return (
		<Card className="my-6">
			<CardContent className="pt-6">
				<Alert
					className={alertVariant({
						stage:
							status.stage === ProcessingStage.ERROR ||
							status.stage === ProcessingStage.COMPLETED
								? status.stage
								: "default",
					})}
				>
					<div className="flex items-center gap-2">
						{stageIcons[status.stage]}
						<AlertTitle>
							{status.stage.charAt(0).toUpperCase() +
								status.stage.slice(1)}
						</AlertTitle>
					</div>
					<AlertDescription>{status.message}</AlertDescription>
					{status.progress !== undefined &&
						status.stage !== ProcessingStage.COMPLETED &&
						status.stage !== ProcessingStage.ERROR && (
							<Progress
								value={status.progress}
								className="mt-2"
							/>
						)}
				</Alert>
			</CardContent>
		</Card>
	);
}
