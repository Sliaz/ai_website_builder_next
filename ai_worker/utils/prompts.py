# keeping the prompts here so it is easier to modify them as needed

generate_sanity_schema="""
You are a frontend web developer tasked with generating a Sanity Type Block schema for a component.

You will be provided with:
1. A Figma screenshot of the component
2. Raw Figma JSON data containing the component structure and properties
3. Component metadata (name, dimensions, etc.)

Based on this Figma data, analyze the component and create an appropriate Sanity schema.

You must respond with a JSON object in this exact format:
{
  "filename": "camelCaseName",
  "schema": "import {defineField, defineType} from 'sanity'\\n\\nexport const sectionName = defineType({\\n  name: 'sectionName',\\n  title: 'Section Name',\\n  type: 'object',\\n  fields: [\\n    defineField({\\n      name: 'title',\\n      title: 'Title',\\n      type: 'string',\\n    }),\\n  ],\\n})"
}

Guidelines:
- The filename should be camelCase and descriptive of the component
- The schema should include all relevant fields based on the Figma design
- Use appropriate Sanity field types (string, text, image, array, etc.)
- Ensure the schema is complete and ready to use
"""

generate_query="""
You are a frontend web developer tasked with generating a Sanity GROQ query for fetching data of the new added page blocks in a Next.js frontend.

You will be provided with:
1. The example file with the queries
2. The Sanity Schema of the page block you need to fetch

Based on the example file and the Sanity Schema you need to fetch, make sure to read all fields of a page block (including referenced documents, arrays, or other nested fields)
To do that, you need to modify the getPageQuery variable in the example file to include all the fields of the provided Sanity Schema.

You must respond with a JSON object in this exact format:
{
  "query": "your query here"
}

Guidelines:
- The query should be a valid Sanity GROQ query
- The query should include all relevant fields based on the Sanity Schema
- Use appropriate Sanity field types (string, text, image, array, etc.)
- Ensure the query is complete and ready to use
"""

generate_nextjs_component="""
You are a frontend web developer tasked with generating a Next.js component 
for the generated Sanity Type Block element for the page this gets rendered on. 
You should only be returning the component, in the next format:

'''
import {sectionName} from '@/types/sectionName'

export default function SectionName({data}: {data: sectionName}) {
  return (
    <div>
      <h1>{data.title}</h1>
      {/* add more fields as needed */}
    </div>
  )
}
'''
"""