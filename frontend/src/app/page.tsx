// src/app/page.tsx
import { MainLayout } from "@/components/layout/main-layout";
import { DatasetBuilder } from "@/components/dataset-builder/index";

export default function Home() {
	return (
		<MainLayout>
			<div className="mx-auto max-w-5xl">
				<h1 className="mb-8 text-center text-3xl font-bold">
					What dataset do you want to build?
				</h1>
				<DatasetBuilder />
			</div>
		</MainLayout>
	);
}
