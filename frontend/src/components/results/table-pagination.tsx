// src/components/results/TablePagination.tsx
import {
	Pagination,
	PaginationContent,
	PaginationEllipsis,
	PaginationItem,
	PaginationLink,
	PaginationNext,
	PaginationPrevious,
} from "@/components/ui/pagination";

interface TablePaginationProps {
	currentPage: number;
	totalPages: number;
	onPageChange: (page: number) => void;
}

export function TablePagination({
	currentPage,
	totalPages,
	onPageChange,
}: TablePaginationProps) {
	if (totalPages <= 1) {
		return null;
	}

	const getPageItems = () => {
		let pages: (number | "ellipsis")[] = [];

		// Always include first page, current page, and last page
		const fixedPages = [1, currentPage, totalPages];

		// Add pages near current page
		for (
			let i = Math.max(2, currentPage - 1);
			i <= Math.min(totalPages - 1, currentPage + 1);
			i++
		) {
			fixedPages.push(i);
		}

		// Sort and deduplicate
		const uniqueSortedPages = [...new Set(fixedPages)].sort(
			(a, b) => a - b
		);

		// Add ellipses where needed
		for (let i = 0; i < uniqueSortedPages.length; i++) {
			pages.push(uniqueSortedPages[i]);

			if (
				i < uniqueSortedPages.length - 1 &&
				uniqueSortedPages[i + 1] - uniqueSortedPages[i] > 1
			) {
				pages.push("ellipsis");
			}
		}

		return pages;
	};

	return (
		<Pagination className="my-4">
			<PaginationContent>
				<PaginationItem>
					<PaginationPrevious
						onClick={() =>
							onPageChange(Math.max(1, currentPage - 1))
						}
						isActive={currentPage === 1}
					/>
				</PaginationItem>

				{getPageItems().map((page, i) =>
					page === "ellipsis" ? (
						<PaginationItem key={`ellipsis-${i}`}>
							<PaginationEllipsis />
						</PaginationItem>
					) : (
						<PaginationItem key={page}>
							<PaginationLink
								isActive={page === currentPage}
								onClick={() => onPageChange(page)}
							>
								{page}
							</PaginationLink>
						</PaginationItem>
					)
				)}

				<PaginationItem>
					<PaginationNext
						onClick={() =>
							onPageChange(Math.min(totalPages, currentPage + 1))
						}
						isActive={currentPage === totalPages}
					/>
				</PaginationItem>
			</PaginationContent>
		</Pagination>
	);
}
