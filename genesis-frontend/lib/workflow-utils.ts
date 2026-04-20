import { z } from "zod";
import { WorkflowManifest } from "@/types/workflow";

export function generateZodSchema(workflow: WorkflowManifest) {
  // We use Record<string, any> here so we can build the object dynamically
  const schemaFields: Record<string, any> = {};

  for (const [key, config] of Object.entries(workflow.inputs)) {
    // 1. Using 'any' here is the key. It prevents the "union not callable" error 
    // when calling .default() or .optional() later.
    let validator: any;

    switch (config.type) {
      case "int":
        // Removed the params from .number() to avoid the invalid_type_error.
        // We put the custom message inside .int() instead.
        validator = z.coerce.number().int(`${key} must be an integer`);
        break;

      case "float":
        validator = z.coerce.number();
        break;

      case "bool":
        // Fix for HTML forms where "false" is a truthy string
        validator = z.preprocess((val) => {
          if (typeof val === "string") {
            if (val.toLowerCase() === "true") return true;
            if (val.toLowerCase() === "false") return false;
          }
          return val;
        }, z.boolean());
        break;

      case "list[file]":
        validator = z.array(z.any());
        break;

      case "file":
      case "dir":
        validator = z.any().nullable();
        break;

      case "list[string]":
        validator = z.array(z.string());
        break;

      case "string":
      default:
        validator = z.string();
        if (config.required) {
          validator = validator.min(1, `${key} is required`);
        }
        break;
    }

    // 2. Handle Defaults (0 and false are valid, so check against undefined/null)
    if (config.default !== undefined && config.default !== null) {
      validator = validator.default(config.default);
    }

    // 3. Handle Optionality
    if (!config.required) {
      if (config.type === "string" || !config.type) {
        // Allows the field to be missing OR be an empty string (common in forms)
        validator = validator.optional().or(z.literal(""));
      } else {
        validator = validator.optional().nullable();
      }
    }

    schemaFields[key] = validator;
  }

  return z.object(schemaFields);
}
