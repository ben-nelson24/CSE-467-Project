export interface StepSpec {
  action: ['goto' | 'click', ...string[]];
  origin?: {
    location: string;
    tagName: string;
    id: string;
    textContent: string;
    text: string;
  };
  reward: number;
}

export interface JobSpec {
  priority: number;
  parents: string[];
  steps: StepSpec[];
}

export interface ElementInformation {
  outerHTML: string;
  tagName: string;
  attributes: { [key: string]: string };
  text: string;
  isVisible: boolean;
}

export interface WebFormField {
  name: string | null;
  fieldElement: ElementInformation;
  labelElement?: ElementInformation;
  previousElement?: ElementInformation;
}

export interface WebForm {
  defaultFormData: { [key: string]: string };
  element: ElementInformation;
  fields: WebFormField[];
  buttons: ElementInformation[];
}
