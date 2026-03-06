from figma_worker.figma_connection import FigmaConnection
from config import settings


def main():
    if not settings.figma_api_key:
        raise ValueError("FIGMA_API_KEY not set in environment")

    figma_project_key = str(input("Enter the Figma Project Key: "))
    figma_proejct_key = figma_project_key.strip()

    figma_connection = FigmaConnection(settings.figma_api_key, figma_project_key)

    # figma_connection.get_developer_variables()

    figma_connection.get_file()

    figma_connection.seed_definitions()

    figma_connection.traverse_pages()

    # figma_connection.hydrate_components()


if __name__ == "__main__":
    main()
