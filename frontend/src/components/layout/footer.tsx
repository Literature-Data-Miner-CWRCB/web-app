// src/components/layout/Footer.tsx
import Link from "next/link";

export function Footer() {
	return (
		<footer className="border-t bg-background">
			<div className="container py-6 md:flex md:items-center md:justify-between">
				<div className="flex justify-center space-x-6 md:justify-start">
					<Link
						href="/about"
						className="text-sm text-muted-foreground hover:text-foreground"
					>
						About
					</Link>
					<Link
						href="/docs"
						className="text-sm text-muted-foreground hover:text-foreground"
					>
						Documentation
					</Link>
					<Link
						href="/privacy"
						className="text-sm text-muted-foreground hover:text-foreground"
					>
						Privacy Policy
					</Link>
				</div>
				<div className="mt-4 text-center text-sm text-muted-foreground md:mt-0">
					&copy; {new Date().getFullYear()} Research Dataset
					Generator. All rights reserved.
				</div>
			</div>
		</footer>
	);
}