// src/components/layout/Header.tsx
import { Button } from "@/components/ui/button";
import { ModeToggle } from "@/components/ui/mode-toggle";
import Link from "next/link";
import Image from "next/image";

export function Header() {
	return (
		<header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
			<div className="flex h-16 items-center justify-between">
				<div className="flex items-center gap-2">
					<Link href="/" className="flex items-center gap-2">
						<Image
							src="/logo.svg"
							alt="Dataset Generator"
							width={32}
							height={32}
							className="h-8 w-8"
						/>
						<span className="hidden font-bold sm:inline-block">
							Dataset Generation From Research Papers
						</span>
					</Link>
				</div>
				<nav className="flex items-center gap-4">
					<ModeToggle />
					<div className="flex items-center gap-2">
						<Button variant="outline" size="sm" asChild>
							<Link href="/login">Login</Link>
						</Button>
						<Button size="sm" asChild>
							<Link href="/signup">Signup</Link>
						</Button>
					</div>
				</nav>
			</div>
		</header>
	);
}