from .figma_connection import FigmaConnection


def main():
    figma_project_key = str(input("Enter the Figma Project Key: "))
    figma_proejct_key = figma_project_key.strip()

    figma_connection = FigmaConnection("12", figma_project_key)


if __name__ == "__main__":
    main()
