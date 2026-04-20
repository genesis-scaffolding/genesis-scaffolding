// Type definition for workflow definition
// Generally matching the pydantic schema defined in the genesis-core

export type WorkflowInputType =
  | "string"
  | "int"
  | "float"
  | "bool"
  | "file"
  | "dir"
  | "list[string]"
  | "list[file]";

export interface InputDefinition {
  type: WorkflowInputType;
  description: string;
  default?: any;
  required: boolean;
}

export interface StepDefinition {
  id: string;
  type: string;
  params: Record<string, any>;
  condition?: string | null;
}

export interface OutputDefinition {
  description: string;
  value: string;
}

export interface WorkflowManifest {
  id: string; // The filename or backend ID
  name: string;
  description: string;
  version: string;
  inputs: Record<string, InputDefinition>;
  steps: StepDefinition[];
  outputs: Record<string, OutputDefinition>;
}
