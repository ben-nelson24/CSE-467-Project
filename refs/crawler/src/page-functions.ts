import {
  StepSpec, ElementInformation, WebFormField, WebForm,
} from './types.js';

export function initFunction() {
  const calledSpecialAPIs: { [key: string]: boolean } = {};
  (window as any).calledSpecialAPIs = calledSpecialAPIs;

  // Geolocation
  const { watchPosition, getCurrentPosition } = window.navigator.geolocation;

  window.navigator.geolocation.watchPosition = function (...args) {
    calledSpecialAPIs['geolocation.watchPostion'] = true;
    return watchPosition.apply(this, args);
  };

  window.navigator.geolocation.getCurrentPosition = function (...args) {
    calledSpecialAPIs['geolocation.getCurrentPosition'] = true;
    return getCurrentPosition.apply(this, args);
  };

  // Motion sensors through window.addEventListener
  const { addEventListener } = window;

  window.addEventListener = function (...args: any[]) {
    const eventName = args[0];

    if (['devicemotion', 'deviceorientation', 'deviceorientationabsolute'].includes(eventName)) {
      calledSpecialAPIs[`eventListener:${eventName}`] = true;
    }

    return addEventListener.apply(this, args as any);
  };

  // Sensors
  if ('Sensor' in window) {
    const { start } = (window as any).Sensor.prototype;

    (window as any).Sensor.prototype.start = function (...args: any[]) {
      calledSpecialAPIs[`${this.constructor.name}.start`] = true;
      return start.apply(this, args);
    };
  }

  // Camera, microphone and screen capture
  const { getUserMedia, getDisplayMedia } = window.MediaDevices.prototype;

  window.MediaDevices.prototype.getUserMedia = function (...args) {
    if (args[0]?.audio) calledSpecialAPIs['MediaDevices.getUserMedia:audio'] = true;
    if (args[0]?.video) calledSpecialAPIs['MediaDevices.getUserMedia:video'] = true;
    return getUserMedia.apply(this, args);
  };

  window.MediaDevices.prototype.getDisplayMedia = function (...args) {
    if (args[0]?.audio) calledSpecialAPIs['MediaDevices.getDisplayMedia:audio'] = true;
    if (args[0]?.video) calledSpecialAPIs['MediaDevices.getDisplayMedia:video'] = true;
    return getDisplayMedia.apply(this, args);
  };

  // Avoid popups
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  window.open = function (url?: string | URL, target?: string, features?: string): Window | null {
    if (url) window.location.replace(url.toString());
    return null;
  };
}

export async function getFormInformation(formElement: HTMLFormElement): Promise<WebForm> {
  function getTrimmedText(element: HTMLElement): string {
    const rawText = element.innerText || element.textContent || '';
    return rawText.split('\n').map((s) => s.trim()).join('\n');
  }

  async function getElementInformation(element: Element): Promise<ElementInformation> {
    return {
      outerHTML: element.outerHTML,
      tagName: element.tagName,
      attributes: [...element.attributes].reduce((o, a) => Object.assign(o, { [a.name]: a.value }), {}),
      text: getTrimmedText(element as HTMLElement),
      isVisible: await (window as any).isElementVisible(formElement),
    };
  }

  const formData = new FormData(formElement);
  const formInfo: WebForm = {
    defaultFormData: Object.fromEntries([...formData].map((o) => [o[0], o[1].toString()])),
    element: await getElementInformation(formElement),
    fields: [],
    buttons: [],
  };

  for (const childElement of formElement.elements) {
    // A button
    if (childElement instanceof HTMLButtonElement
        || (childElement instanceof HTMLInputElement && childElement.type === 'submit')
        || (childElement.role === 'button')) {
      formInfo.buttons.push(await getElementInformation(childElement));
      continue;
    }

    // A general form field
    const fieldInfo: WebFormField = {
      name: (childElement as HTMLInputElement).name || null,
      fieldElement: await getElementInformation(childElement),
    };

    formInfo.fields.push(fieldInfo);

    // Find the label associated with the input element
    if (childElement.id) {
      const e = formElement.querySelector<HTMLElement>(`label[for="${childElement.id}"]`);
      if (e !== null) fieldInfo.labelElement = await getElementInformation(e);
    }

    // If no label, provide the previous (visible) element as a hint
    if (fieldInfo.labelElement === undefined) {
      const otherFields = Array
        .from(formElement.elements)
        .filter((o) => (o as HTMLInputElement).name !== fieldInfo.name && o !== childElement);
      let previousElement = null;

      for (
        let e: Element | null = childElement;
        previousElement === null && formElement.contains(e) && !!e && otherFields.every((o) => !e?.contains(o));
        e = e.parentElement
      ) {
        for (
          let sibling = e.previousElementSibling;
          sibling !== null && otherFields.every((o) => !sibling?.contains(o));
          sibling = sibling?.previousElementSibling) {
          if ((sibling as HTMLElement).innerText) {
            previousElement = sibling;
            break;
          }
        }
      }

      if (previousElement !== null) {
        fieldInfo.previousElement = await getElementInformation(previousElement);
      }
    }
  }

  return formInfo;
}

/**
 * Patch non-form fields to make them wrapped in a form element
 */
export async function patchNonFormFields() {
  function getAncestors(node: HTMLElement) {
    const nodes = [node];
    for (let n = node; n; n = n.parentElement!) nodes.unshift(n);
    return nodes;
  }

  function getFirstCommonParent(node1: HTMLElement, node2: HTMLElement): HTMLElement | null {
    const parents1 = getAncestors(node1);
    const parents2 = getAncestors(node2);
    let commonParent = null;

    while (parents1.length > 0 && parents1[0] === parents2[0]) {
      commonParent = parents1.shift()!;
      parents2.shift();
    }

    return commonParent;
  }

  const elements = [];

  for (const labelElement of document.body.querySelectorAll<HTMLElement>('label[for]')) {
    let inputElement = null;
    let containerElement = null;

    if (!labelElement.hasAttribute('data-flag-visited')
        && (inputElement = document.getElementById(labelElement.getAttribute('for') || ''))
        && (containerElement = getFirstCommonParent(inputElement, labelElement))
        && ['INPUT', 'SELECT', 'TEXTAREA'].includes(inputElement.tagName)
        && (inputElement as HTMLInputElement).form === null) {
      elements.push(containerElement);

      for (let idx = 0; idx < elements.length - 1; idx += 1) {
        const commonParent = getFirstCommonParent(containerElement, elements[idx]);

        if (commonParent !== null
            && commonParent !== document.body
            && commonParent.querySelector('form') === null) {
          elements[idx] = commonParent;
          elements.pop();
          break;
        }
      }
    }
  }

  for (const e of elements) {
    const style = window.getComputedStyle(e);
    const newNode = document.createElement('form');

    Array.from(e.attributes).forEach((attr) => newNode.setAttribute(attr.name, attr.value));
    Array.from(style).forEach(
      (key) => newNode.style.setProperty(key, style.getPropertyValue(key), style.getPropertyPriority(key)),
    );
    newNode.setAttribute('data-old-tag', e.tagName);
    newNode.setAttribute('data-testid', 'patched-form');
    newNode.innerHTML = e.innerHTML;

    e.replaceWith(newNode);
  }
}

export function markInterestingElements() {
  for (const element of document.body.querySelectorAll('*')) {
    if (['link', 'button', 'form', 'label'].includes(element.role || '')
        || ['A', 'BUTTON', 'FORM', 'LABEL'].includes(element.tagName)) {
      element.setAttribute('data-flag-visited', '');
    }
  }
}

export async function findNextSteps(): Promise<StepSpec[]> {
  // Ref: https://gist.github.com/iiLaurens/81b1b47f6259485c93ce6f0cdd17490a
  let clickableElements: Element[] = [];

  for (const element of document.body.querySelectorAll<HTMLElement>(
    // Skip visited and disabled elements
    '*:not([data-flag-visited]):not([disabled]):not([aria-disabled="true"])',
  )) {
    if (!!(element).onclick
        || ['link', 'button'].includes(element.role || '')
        || ['A', 'BUTTON'].includes(element.tagName)) {
      clickableElements.push(element);
    }
  }

  // Only keep inner clickable items
  clickableElements = clickableElements.filter((x) => !clickableElements.some((y) => x.contains(y) && x !== y));

  const possibleSteps: StepSpec[] = [];

  for (const element of clickableElements) {
    const origin = {
      location: window.location.href,
      tagName: element.tagName,
      id: element.id,
      textContent: element.textContent || '',
      text: ((element as HTMLElement).innerText || element.getAttribute('aria-label') || '').trim().toString(),
    };

    if (element instanceof HTMLAnchorElement && element.onclick === null && !!element.href.match(/^https?:/)) {
      // A pure anchor element
      const parsedUrl = new URL(element.href);
      parsedUrl.hash = '';

      possibleSteps.push({
        action: ['goto', parsedUrl.href],
        origin,
        reward: NaN,
      });
    } else {
      // Something else that is clickable
      possibleSteps.push({
        action: ['click', await (window as any).hashObjectSha256(origin)],
        origin,
        reward: NaN,
      });
    }
  }

  return possibleSteps;
}
