// src/components/results/CitationDisplay.tsx
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import {
	Accordion,
	AccordionContent,
	AccordionItem,
	AccordionTrigger,
} from "@/components/ui/accordion";
import { ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Citation } from "@/types/events";

interface CitationDisplayProps {
	citations: Citation[];
}

export function CitationDisplay({ citations }: CitationDisplayProps) {
	if (citations.length === 0) {
		return null;
	}

	return (
		<Card className="mt-6">
			<CardHeader>
				<CardTitle>Citations</CardTitle>
				<CardDescription>
					The dataset was generated using the following research
					papers:
				</CardDescription>
			</CardHeader>
			<CardContent>
				<Accordion type="multiple" className="w-full">
					{citations.map((citation) => (
						<AccordionItem key={citation.id} value={citation.id}>
							<AccordionTrigger className="text-left">
								{citation.title} ({citation.year})
							</AccordionTrigger>
							<AccordionContent>
								<div className="space-y-2 pl-4">
									<p>
										<span className="font-medium">
											Authors:
										</span>{" "}
										{citation.authors.join(", ")}
									</p>
									{citation.journal && (
										<p>
											<span className="font-medium">
												Journal:
											</span>{" "}
											{citation.journal}
										</p>
									)}
									{citation.doi && (
										<p>
											<span className="font-medium">
												DOI:
											</span>{" "}
											{citation.doi}
										</p>
									)}
									{citation.url && (
										<Button
											variant="link"
											className="h-auto p-0"
											asChild
										>
											<a
												href={citation.url}
												target="_blank"
												rel="noopener noreferrer"
												className="flex items-center text-primary"
											>
												View paper{" "}
												<ExternalLink className="ml-1 h-3 w-3" />
											</a>
										</Button>
									)}
								</div>
							</AccordionContent>
						</AccordionItem>
					))}
				</Accordion>
			</CardContent>
		</Card>
	);
}
