import { getProjectsAction } from "@/app/actions/productivity";
import { PageContainer, PageBody } from "@/components/dashboard/page-container";
import { ProjectCard } from "@/components/dashboard/projects/project-card";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";
import Link from "next/link";

export default async function ProjectsPage() {
  const projects = await getProjectsAction();

  return (
    <PageContainer variant="dashboard">
      <PageBody>
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Projects</h1>
            <p className="text-muted-foreground">
              Manage your long-term goals and project-specific tasks.
            </p>
          </div>
          <Button asChild>
            <Link href="/dashboard/projects/create">
              <Plus className="mr-2 h-4 w-4" /> New Project
            </Link>
          </Button>
        </div>

        {projects.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 border-2 border-dashed rounded-lg">
            <p className="text-muted-foreground mb-4">No projects found.</p>
            <Button variant="outline" asChild>
              <Link href="/dashboard/projects/create">Create your first project</Link>
            </Button>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {projects.map((project) => (
              <ProjectCard key={project.id} project={project} />
            ))}
          </div>
        )}
      </PageBody>
    </PageContainer>
  );
}
