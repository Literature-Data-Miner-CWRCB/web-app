// src/components/layout/MainLayout.tsx
import { ReactNode } from "react";
import { Header } from "./header";
import { Footer } from "./footer";

interface MainLayoutProps {
	children: ReactNode;
}

export function MainLayout({ children }: MainLayoutProps) {
	return (
		<div className="flex min-h-screen flex-col">
			<Header />
			<main className="flex-1 py-6 md:py-10">
				<div>{children}</div>
			</main>
			<Footer />
		</div>
	);
}
