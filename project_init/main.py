from pathlib import Path
import os
import subprocess

from .runner import run, run_capture
from .env_writer import write_env_files
from .scaffold import setup_visual_editing


SANITY_TEMPLATES = [
    ("clean", "Empty Studio (clean slate)"),
    ("blog", "Blog (posts, authors, categories)"),
    ("moviedb", "Movie Database (movies, actors, directors)"),
    ("shopify", "Shopify (products, collections, categories)"),
]


def is_sanity_authenticated() -> bool:
    """Best-effort signal for whether the user is logged into the Sanity CLI."""
    if os.getenv("SANITY_AUTH_TOKEN"):
        return True

    sanity_rc = Path.home() / ".sanityrc"
    if sanity_rc.exists():
        try:
            content = sanity_rc.read_text()
        except Exception:
            return True

        if "authToken" in content or "cliToken" in content or content.strip():
            return True

    return False


def get_sanity_projects() -> list[dict]:
    """Get list of Sanity projects by parsing CLI output."""
    try:
        result = run_capture(["npx", "sanity@latest", "projects", "list"])
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            projects = []
            for line in lines[2:]:  # Skip header and separator
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 4:
                        project_id = parts[0]
                        name = parts[3] if len(parts) > 3 else "Unnamed"
                        projects.append({"projectId": project_id, "name": name})
            return projects
    except Exception:
        pass
    return []


def main():
    project_name = str(input("Enter this project's name: "))

    BUILDER_ROOT = Path(__file__).resolve().parent.parent
    OUTPUT_DIR = BUILDER_ROOT / project_name

    OUTPUT_DIR.mkdir(exist_ok=True)

    print(f"\nCreating Next.js frontend in: {OUTPUT_DIR}")
    run(
        [
            "npx",
            "create-next-app@latest",
            "frontend",
            "--ts",
            "--tailwind",
            "--app",
            "--src-dir",
            "--yes",
        ],
        cwd=OUTPUT_DIR,
    )

    # Prompt for template
    print("\nSelect Sanity Studio template:")
    for i, (name, desc) in enumerate(SANITY_TEMPLATES, 1):
        print(f"  {i}. {desc} (template: {name})")

    template_choice = input("Select template (number): ").strip()
    try:
        choice_num = int(template_choice)
        if 1 > choice_num or choice_num > len(SANITY_TEMPLATES):
            template_idx = 0
        else:
            template_idx = choice_num - 1
    except ValueError:
        template_idx = 0
    template = SANITY_TEMPLATES[template_idx][0]
    print(f"\n>>> DEBUG: Selected template: '{template}' (choice: '{template_choice}')")

    # Check for existing projects if authenticated
    projects: list[dict] = []
    if is_sanity_authenticated():
        projects = get_sanity_projects()
    else:
        print("\n(Sanity CLI not authenticated; skipping project lookup. Run `npx sanity login` or set SANITY_AUTH_TOKEN to enable auto-selection.)")

    project_id = None

    if projects:
        print(f"\n--- Sanity Projects Found ---")
        for i, p in enumerate(projects, 1):
            print(f"  {i}. {p.get('name', 'Unnamed')} ({p.get('projectId', 'N/A')})")
        print(f"  0. Skip (create manually)")

        proj_choice = input("\nSelect a project (number): ").strip()
        if proj_choice.isdigit() and 1 <= int(proj_choice) <= len(projects):
            project_id = projects[int(proj_choice) - 1].get("projectId", "")
            print(f"  Using project: {project_id}")

    if not project_id:
        manual_project = input("\nEnter an existing Sanity project ID (leave blank to skip): ").strip()
        if manual_project:
            project_id = manual_project
            print(f"  Using manually provided project: {project_id}")

    # Create studio directory
    studio_dir = OUTPUT_DIR / "studio"
    studio_dir.mkdir(exist_ok=True)

    print(f"\n--- Setting up Sanity Studio ---\n")
    print(f"Creating studio with template: {template}")

    cmd = [
        "npx",
        "sanity@latest",
        "init",
        "--no-mcp",
        "--template",
        template,
        "--dataset",
        "production",
        "--output-path",
        str(studio_dir),
        "--no-typescript" if template == "clean" else "--typescript",
    ]

    if project_id:
        cmd.insert(3, "-y")
        cmd.extend(["--project-id", project_id])
    else:
        print(
            "\nNo project ID detected; running Sanity init interactively so you can log in or create a project."
        )

    print(f"\n>>> DEBUG: Running command: {' '.join(cmd)}")

    try:
        run(cmd, cwd=OUTPUT_DIR)
        print("\n✓ Sanity Studio created successfully!")
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Failed to create Sanity Studio (exit {e.returncode})")
        print("You can create it manually:")
        print(f"  cd {OUTPUT_DIR / 'studio'}")
        manual_project = project_id or "YOUR_PROJECT_ID"
        print(
            f"  sanity init -- --dataset production --template {template} --project-id {manual_project}"
        )
    except Exception as e:
        print(f"\n✗ Failed to create Sanity Studio: {e}")
        print("You can create it manually:")
        print(f"  cd {OUTPUT_DIR / 'studio'}")
        manual_project = project_id or "YOUR_PROJECT_ID"
        print(
            f"  sanity init -- --dataset production --template {template} --project-id {manual_project}"
        )

    # Try to find project ID from created studio
    env_path = studio_dir / ".env"
    if not project_id and env_path.exists():
        content = env_path.read_text()
        for line in content.split("\n"):
            if line.startswith("SANITY_PROJECT_ID="):
                project_id = line.split("=", 1)[1].strip()
                break

    # Generate env files
    write_env_files(OUTPUT_DIR, project_id=project_id)

    setup_visual_editing(OUTPUT_DIR, project_name)

    print(f"\n--- Project Setup Complete! ---\n")
    print(f"Project: {project_name}")
    print(f"Location: {OUTPUT_DIR}")
    print(f"  - Frontend: {OUTPUT_DIR / 'frontend'}")
    print(f"  - Studio:   {OUTPUT_DIR / 'studio'}")

    print("\n=== ALL DONE ===")
    print("\nNext steps:")
    print("1. Update SANITY_VIEWER_TOKEN in frontend/.env.local")
    print("   Run: npx sanity manage")
    print("   Create a token with Viewer permission")
    print("2. Start frontend: cd frontend && npm run dev")
    print("3. Start studio:   cd studio  && npm run dev")


if __name__ == "__main__":
    main()
