const DOMAIN = "homepass";
const PREPARE_NFC_TAG_ACTION = "prepare_nfc_tag";
const CONFIRM_NFC_TAG_PROTECTION_ACTION = "confirm_nfc_tag_protection";
const CREATE_NFC_TEST_TAG_ACTION = "create_nfc_test_tag";
const GET_NFC_TEST_TAG_STATUS_ACTION = "get_nfc_test_tag_status";
const REVOKE_NFC_TEST_TAG_ACTION = "revoke_nfc_test_tag";

// GoToTags' documented NTAG424 PICC Data and MAC Mirroring encoding-file fields.
// Keep these names aligned with the vendor CSV so the file can be imported into
// a Variable Encode NFC Tags operation without manually re-entering secrets.
const GOTOTAGS_NTAG424_COLUMNS = Object.freeze([
  "lock",
  "ndef.records.0.type",
  "ndef.records.0.url",
  "chip.ntag424.files.ccFileAccessRights.readCondition",
  "chip.ntag424.files.ccFileAccessRights.writeCondition",
  "chip.ntag424.files.ccFileAccessRights.readWriteCondition",
  "chip.ntag424.files.ccFileAccessRights.changeCondition",
  "chip.ntag424.files.ndefFileAccessRights.readCondition",
  "chip.ntag424.files.ndefFileAccessRights.writeCondition",
  "chip.ntag424.files.ndefFileAccessRights.readWriteCondition",
  "chip.ntag424.files.ndefFileAccessRights.changeCondition",
  "chip.ntag424.files.proprietaryFileAccessRights.readCondition",
  "chip.ntag424.files.proprietaryFileAccessRights.writeCondition",
  "chip.ntag424.files.proprietaryFileAccessRights.readWriteCondition",
  "chip.ntag424.files.proprietaryFileAccessRights.changeCondition",
  "chip.ntag424.newKeys.key0",
  "chip.ntag424.newKeys.key0Diversified",
  "chip.ntag424.currentKeys.key0",
  "chip.ntag424.currentKeys.key0Diversified",
  "chip.ntag424.newKeys.key1",
  "chip.ntag424.newKeys.key1Diversified",
  "chip.ntag424.currentKeys.key1",
  "chip.ntag424.currentKeys.key1Diversified",
  "chip.ntag424.newKeys.key2",
  "chip.ntag424.newKeys.key2Diversified",
  "chip.ntag424.currentKeys.key2",
  "chip.ntag424.currentKeys.key2Diversified",
  "chip.ntag424.newKeys.key3",
  "chip.ntag424.newKeys.key3Diversified",
  "chip.ntag424.currentKeys.key3",
  "chip.ntag424.currentKeys.key3Diversified",
  "chip.ntag424.newKeys.key4",
  "chip.ntag424.newKeys.key4Diversified",
  "chip.ntag424.currentKeys.key4",
  "chip.ntag424.currentKeys.key4Diversified",
  "chip.ntag424.sdmSettings.accessRights.fileRead",
  "chip.ntag424.sdmSettings.accessRights.metaRead",
  "chip.ntag424.sdmSettings.accessRights.readCounter",
  "chip.ntag424.sdmSettings.offsets.piccData",
  "chip.ntag424.sdmSettings.offsets.macInput",
  "chip.ntag424.sdmSettings.offsets.mac",
  "chip.ntag424.sdmSettings.options.encryptFileData",
  "chip.ntag424.sdmSettings.options.readCounter",
  "chip.ntag424.sdmSettings.options.readCounterLimit",
  "chip.ntag424.sdmSettings.options.uidMirroring",
]);

const escapeHtml = (value) =>
  String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

const csvCell = (value) => {
  const text = String(value ?? "");
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
};

const gototagsProfile = (templateValue) => {
  const template = String(templateValue ?? "");
  const urlPrefix = "https://";
  const piccMarker = "?e=";
  const macMarker = "&c=";
  const piccStart = template.indexOf(piccMarker) + piccMarker.length;
  const macStart = template.indexOf(macMarker, piccStart) + macMarker.length;
  if (
    !template.startsWith(urlPrefix) ||
    piccStart < piccMarker.length ||
    macStart < macMarker.length ||
    !/^0{32}$/.test(template.slice(piccStart, piccStart + 32)) ||
    !/^0{16}$/.test(template.slice(macStart, macStart + 16))
  ) throw new Error("HomePASS returned an unsupported NTAG424 URL template.");
  const encodedOffset = (urlIndex) =>
    7 + new TextEncoder().encode(template.slice(urlPrefix.length, urlIndex)).length;
  const piccData = encodedOffset(piccStart);
  const mac = encodedOffset(macStart);
  return {piccData, macInput: mac, mac};
};

const goToTagsNtag424Values = (
  result,
  existingTag = false,
  permanentlyLock = false,
) => {
  const offsets = gototagsProfile(result?.ndef_url_template);
  const factoryKey = "00000000000000000000000000000000";
  const currentFileKey = existingTag ? result.file_read_key : factoryKey;
  const currentMetaKey = existingTag ? result.meta_read_key : factoryKey;
  return {
    lock: permanentlyLock ? "TRUE" : "FALSE",
    "ndef.records.0.type": "WEBSITE",
    "ndef.records.0.url": result.ndef_url_template,
    "chip.ntag424.files.ccFileAccessRights.readCondition": "FREE",
    "chip.ntag424.files.ccFileAccessRights.writeCondition": "APP_KEY_0",
    "chip.ntag424.files.ccFileAccessRights.readWriteCondition": "APP_KEY_0",
    "chip.ntag424.files.ccFileAccessRights.changeCondition": "APP_KEY_0",
    "chip.ntag424.files.ndefFileAccessRights.readCondition": "FREE",
    "chip.ntag424.files.ndefFileAccessRights.writeCondition": "APP_KEY_0",
    "chip.ntag424.files.ndefFileAccessRights.readWriteCondition": "APP_KEY_0",
    "chip.ntag424.files.ndefFileAccessRights.changeCondition": "APP_KEY_0",
    "chip.ntag424.files.proprietaryFileAccessRights.readCondition": "APP_KEY_2",
    "chip.ntag424.files.proprietaryFileAccessRights.writeCondition": "APP_KEY_3",
    "chip.ntag424.files.proprietaryFileAccessRights.readWriteCondition": "APP_KEY_3",
    "chip.ntag424.files.proprietaryFileAccessRights.changeCondition": "APP_KEY_0",
    "chip.ntag424.newKeys.key0": result.admin_key,
    "chip.ntag424.newKeys.key0Diversified": "FALSE",
    "chip.ntag424.currentKeys.key0": result.current_admin_key || factoryKey,
    "chip.ntag424.currentKeys.key0Diversified": "FALSE",
    "chip.ntag424.newKeys.key1": result.file_read_key,
    "chip.ntag424.newKeys.key1Diversified": "FALSE",
    "chip.ntag424.currentKeys.key1": currentFileKey,
    "chip.ntag424.currentKeys.key1Diversified": "FALSE",
    "chip.ntag424.newKeys.key2": result.meta_read_key,
    "chip.ntag424.newKeys.key2Diversified": "FALSE",
    "chip.ntag424.currentKeys.key2": currentMetaKey,
    "chip.ntag424.currentKeys.key2Diversified": "FALSE",
    "chip.ntag424.newKeys.key3": factoryKey,
    "chip.ntag424.newKeys.key3Diversified": "FALSE",
    "chip.ntag424.currentKeys.key3": factoryKey,
    "chip.ntag424.currentKeys.key3Diversified": "FALSE",
    "chip.ntag424.newKeys.key4": factoryKey,
    "chip.ntag424.newKeys.key4Diversified": "FALSE",
    "chip.ntag424.currentKeys.key4": factoryKey,
    "chip.ntag424.currentKeys.key4Diversified": "FALSE",
    "chip.ntag424.sdmSettings.accessRights.fileRead": "APP_KEY_1",
    "chip.ntag424.sdmSettings.accessRights.metaRead": "APP_KEY_2",
    "chip.ntag424.sdmSettings.accessRights.readCounter": "FREE",
    "chip.ntag424.sdmSettings.offsets.piccData": offsets.piccData,
    "chip.ntag424.sdmSettings.offsets.macInput": offsets.macInput,
    "chip.ntag424.sdmSettings.offsets.mac": offsets.mac,
    "chip.ntag424.sdmSettings.options.encryptFileData": "FALSE",
    "chip.ntag424.sdmSettings.options.readCounter": "TRUE",
    "chip.ntag424.sdmSettings.options.readCounterLimit": "FALSE",
    "chip.ntag424.sdmSettings.options.uidMirroring": "TRUE",
  };
};

export const buildGoToTagsNtag424Csv = (
  result,
  existingTag = false,
  permanentlyLock = false,
) => {
  const values = goToTagsNtag424Values(result, existingTag, permanentlyLock);
  return `${GOTOTAGS_NTAG424_COLUMNS.join(",")}\n${GOTOTAGS_NTAG424_COLUMNS.map((column) => csvCell(values[column])).join(",")}\n`;
};

const booleanValue = (value) => String(value).toUpperCase() === "TRUE";

const operationId = () => {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  const bytes = new Uint8Array(9);
  globalThis.crypto?.getRandomValues?.(bytes);
  return Array.from(bytes, (value) => alphabet[value % alphabet.length]).join("");
};

const operationEncoding = (values) => ({
  chip: {
    ntag424: {
      files: {
        ccFileAccessRights: {
          readCondition: values["chip.ntag424.files.ccFileAccessRights.readCondition"],
          writeCondition: values["chip.ntag424.files.ccFileAccessRights.writeCondition"],
          readWriteCondition: values["chip.ntag424.files.ccFileAccessRights.readWriteCondition"],
          changeCondition: values["chip.ntag424.files.ccFileAccessRights.changeCondition"],
        },
        ndefFileAccessRights: {
          readCondition: values["chip.ntag424.files.ndefFileAccessRights.readCondition"],
          writeCondition: values["chip.ntag424.files.ndefFileAccessRights.writeCondition"],
          readWriteCondition: values["chip.ntag424.files.ndefFileAccessRights.readWriteCondition"],
          changeCondition: values["chip.ntag424.files.ndefFileAccessRights.changeCondition"],
        },
        proprietaryFileAccessRights: {
          readCondition: values["chip.ntag424.files.proprietaryFileAccessRights.readCondition"],
          writeCondition: values["chip.ntag424.files.proprietaryFileAccessRights.writeCondition"],
          readWriteCondition: values["chip.ntag424.files.proprietaryFileAccessRights.readWriteCondition"],
          changeCondition: values["chip.ntag424.files.proprietaryFileAccessRights.changeCondition"],
        },
      },
      newKeys: Object.fromEntries(Array.from({length: 5}, (_, index) => [
        [`key${index}`, values[`chip.ntag424.newKeys.key${index}`]],
        [`key${index}Diversified`, booleanValue(values[`chip.ntag424.newKeys.key${index}Diversified`])],
      ]).flat()),
      currentKeys: Object.fromEntries(Array.from({length: 5}, (_, index) => [
        [`key${index}`, values[`chip.ntag424.currentKeys.key${index}`]],
        [`key${index}Diversified`, booleanValue(values[`chip.ntag424.currentKeys.key${index}Diversified`])],
      ]).flat()),
      sdmSettings: {
        accessRights: {
          fileRead: values["chip.ntag424.sdmSettings.accessRights.fileRead"],
          metaRead: values["chip.ntag424.sdmSettings.accessRights.metaRead"],
          readCounter: values["chip.ntag424.sdmSettings.accessRights.readCounter"],
        },
        offsets: {
          piccData: Number(values["chip.ntag424.sdmSettings.offsets.piccData"]),
          macInput: Number(values["chip.ntag424.sdmSettings.offsets.macInput"]),
          mac: Number(values["chip.ntag424.sdmSettings.offsets.mac"]),
        },
        options: {
          enabled: true,
          encryptFileData: booleanValue(values["chip.ntag424.sdmSettings.options.encryptFileData"]),
          encodingMode: "ASCII",
          readCounter: booleanValue(values["chip.ntag424.sdmSettings.options.readCounter"]),
          readCounterLimit: booleanValue(values["chip.ntag424.sdmSettings.options.readCounterLimit"]),
          uidMirroring: booleanValue(values["chip.ntag424.sdmSettings.options.uidMirroring"]),
        },
      },
    },
  },
  dynamic: false,
  extra: {},
  lock: booleanValue(values.lock),
  ndef: {
    records: [{type: "WEBSITE", url: values["ndef.records.0.url"]}],
  },
});

const operationTemplateEncoding = () => {
  const factoryKey = "00000000000000000000000000000000";
  const keys = Object.fromEntries(Array.from({length: 5}, (_, index) => [
    [`key${index}`, factoryKey],
    [`key${index}Diversified`, false],
  ]).flat());
  return {
    chip: {
      ntag424: {
        files: {
          ccFileAccessRights: {
            readCondition: "FREE",
            writeCondition: "APP_KEY_0",
            readWriteCondition: "APP_KEY_0",
            changeCondition: "APP_KEY_0",
          },
          ndefFileAccessRights: {
            readCondition: "FREE",
            writeCondition: "FREE",
            readWriteCondition: "FREE",
            changeCondition: "APP_KEY_0",
          },
          proprietaryFileAccessRights: {
            readCondition: "APP_KEY_2",
            writeCondition: "APP_KEY_3",
            readWriteCondition: "APP_KEY_3",
            changeCondition: "APP_KEY_0",
          },
        },
        newKeys: {...keys},
        currentKeys: {...keys},
      },
    },
    dynamic: false,
    extra: {},
  };
};

export const buildGoToTagsNtag424Operation = (
  result,
  existingTag = false,
  name = "HomePASS NFC tag",
  permanentlyLock = false,
) => {
  const now = new Date().toISOString();
  const values = goToTagsNtag424Values(result, existingTag, permanentlyLock);
  return {
    elapsedTime: "PT0S",
    externalId: "",
    chipType: "NTAG424",
    createdAt: now,
    id: operationId(),
    integrations: [],
    name: String(name || "HomePASS NFC tag").slice(0, 100),
    operationType: "VARIABLE_ENCODE_NFC_TAGS",
    options: {
      autoSelectNextTag: "TOP_TO_BOTTOM",
      enforceTiming: false,
      enforceIdOrder: false,
      queueIdsOnScan: false,
      verify: true,
    },
    revision: 3,
    tag: {encoding: operationTemplateEncoding()},
    tags: [{encoding: operationEncoding(values), order: 1, status: "READY"}],
    type: "VARIABLE_ENCODE_NFC_TAGS",
    updatedAt: now,
  };
};

const crc32 = (bytes) => {
  let crc = 0xffffffff;
  for (const byte of bytes) {
    crc ^= byte;
    for (let bit = 0; bit < 8; bit += 1) {
      crc = (crc >>> 1) ^ (0xedb88320 & -(crc & 1));
    }
  }
  return (crc ^ 0xffffffff) >>> 0;
};

const writeUint16 = (view, offset, value) => view.setUint16(offset, value, true);
const writeUint32 = (view, offset, value) => view.setUint32(offset, value, true);

const storedZip = (filename, contents) => {
  const nameBytes = new TextEncoder().encode(filename);
  const dataBytes = new TextEncoder().encode(contents);
  const localSize = 30 + nameBytes.length + dataBytes.length;
  const centralSize = 46 + nameBytes.length;
  const output = new Uint8Array(localSize + centralSize + 22);
  const view = new DataView(output.buffer);
  const checksum = crc32(dataBytes);

  writeUint32(view, 0, 0x04034b50);
  writeUint16(view, 4, 20);
  writeUint16(view, 6, 0x0800);
  writeUint16(view, 8, 0);
  writeUint32(view, 14, checksum);
  writeUint32(view, 18, dataBytes.length);
  writeUint32(view, 22, dataBytes.length);
  writeUint16(view, 26, nameBytes.length);
  output.set(nameBytes, 30);
  output.set(dataBytes, 30 + nameBytes.length);

  const central = localSize;
  writeUint32(view, central, 0x02014b50);
  writeUint16(view, central + 4, 20);
  writeUint16(view, central + 6, 20);
  writeUint16(view, central + 8, 0x0800);
  writeUint16(view, central + 10, 0);
  writeUint32(view, central + 16, checksum);
  writeUint32(view, central + 20, dataBytes.length);
  writeUint32(view, central + 24, dataBytes.length);
  writeUint16(view, central + 28, nameBytes.length);
  output.set(nameBytes, central + 46);

  const end = localSize + centralSize;
  writeUint32(view, end, 0x06054b50);
  writeUint16(view, end + 8, 1);
  writeUint16(view, end + 10, 1);
  writeUint32(view, end + 12, centralSize);
  writeUint32(view, end + 16, localSize);
  return output;
};

export const buildGoToTagsNtag424OperationBlob = (
  result,
  existingTag = false,
  name = "HomePASS NFC tag",
  permanentlyLock = false,
) => {
  const operation = buildGoToTagsNtag424Operation(
    result,
    existingTag,
    name,
    permanentlyLock,
  );
  const archive = storedZip("file.gototags", `${JSON.stringify(operation, null, 2)}\n`);
  return new Blob([archive], {type: "application/zip"});
};

export class HomepassNfcProvisioner extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._uid = "";
    this._busy = false;
    this._error = "";
    this._notice = "";
    this._result = undefined;
    this._permanentlyLock = false;
    this._manualSetup = false;
    this._confirmingProtection = false;
    this._testLoading = true;
    this._testBusy = false;
    this._testError = "";
    this._testNotice = "";
    this._testStatus = undefined;
    this._testResult = undefined;
  }

  connectedCallback() {
    this._render();
  }

  get _doorId() {
    return this.getAttribute("access-point-id") ?? "";
  }

  get _doorName() {
    return this.getAttribute("door-name") || "this door";
  }

  get _panel() {
    return this.getRootNode()?.host;
  }

  get _hass() {
    return this._panel?._hass;
  }

  _normalizedUid(value) {
    return String(value ?? "")
      .toUpperCase()
      .replace(/[^0-9A-F]/g, "")
      .slice(0, 14);
  }

  _validUid() {
    return /^[0-9A-F]{14}$/.test(this._uid);
  }

  async _prepareTag() {
    if (this._busy || !this._validUid() || !this._doorId) return;
    if (!this._hass?.callWS) {
      this._error = "HomePASS is not connected to Home Assistant.";
      this._render();
      return;
    }

    this._busy = true;
    this._error = "";
    this._notice = "";
    this._result = undefined;
    this._render();

    let prepared = false;
    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: PREPARE_NFC_TAG_ACTION,
        service_data: {
          access_point_id: this._doorId,
          uid_hex: this._uid,
        },
        return_response: true,
      });
      const response = result?.response;
      if (
        !response?.public_id ||
        !response?.ndef_url_template ||
        !response?.meta_read_key ||
        !response?.file_read_key ||
        !response?.admin_key
      ) {
        throw new Error("HomePASS did not return a complete provisioning package.");
      }
      this._result = {
        ...response,
        uid_hex: this._uid,
        access_point_id: this._doorId,
        door_name: this._doorName,
        generated_at: new Date().toISOString(),
      };
      this._notice = "Secure setup created. Write these values to this NTAG424 DNA tag now.";
      prepared = true;
    } catch (error) {
      this._error =
        error?.message ||
        "HomePASS could not prepare this NFC tag. Confirm the UID and try again.";
    } finally {
      this._busy = false;
      this._render();
    }
    if (prepared) {
      this.dispatchEvent(new CustomEvent("homepass-nfc-tag-prepared", {
        bubbles: true,
        composed: true,
        detail: {access_point_id: this._doorId},
      }));
    }
  }

  async _loadTestStatus() {
    if (!this._doorId || !this._hass?.callWS) {
      this._testLoading = false;
      this._testError = "HomePASS could not load NTAG216 test-tag status.";
      this._render();
      return;
    }
    this._testLoading = true;
    this._testError = "";
    this._render();
    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: GET_NFC_TEST_TAG_STATUS_ACTION,
        service_data: {access_point_id: this._doorId},
        return_response: true,
      });
      this._testStatus = result?.response ?? {active: false};
    } catch (error) {
      this._testError = error?.message || "HomePASS could not load NTAG216 test-tag status.";
    } finally {
      this._testLoading = false;
      this._render();
    }
  }

  async _createTestTag() {
    if (this._testBusy || this._testStatus?.active || !this._doorId) return;
    this._testBusy = true;
    this._testError = "";
    this._testNotice = "";
    this._testResult = undefined;
    this._render();
    try {
      const result = await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: CREATE_NFC_TEST_TAG_ACTION,
        service_data: {access_point_id: this._doorId, expires_in_hours: 168},
        return_response: true,
      });
      const response = result?.response;
      if (!response?.active || !response?.test_url || !response?.expires_at) {
        throw new Error("HomePASS did not return a complete NTAG216 test URL.");
      }
      this._testResult = response;
      this._testStatus = {active: true, expires_at: response.expires_at};
      this._testNotice = "Test URL created. Write this Nabu Casa URL to the NTAG216.";
    } catch (error) {
      this._testError = error?.message || "HomePASS could not create the NTAG216 test URL.";
    } finally {
      this._testBusy = false;
      this._render();
    }
  }

  async _revokeTestTag() {
    if (this._testBusy || !this._testStatus?.active || !this._doorId) return;
    if (!globalThis.confirm(
      `Revoke the NTAG216 test tag for ${this._doorName}? The written tag will stop working immediately.`,
    )) return;
    this._testBusy = true;
    this._testError = "";
    this._testNotice = "";
    this._render();
    try {
      await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: REVOKE_NFC_TEST_TAG_ACTION,
        service_data: {access_point_id: this._doorId},
        return_response: true,
      });
      this._testStatus = {active: false, expires_at: null};
      this._testResult = undefined;
      this._testNotice = "NTAG216 test tag revoked. It can no longer unlock this door.";
    } catch (error) {
      this._testError = error?.message || "HomePASS could not revoke the NTAG216 test tag.";
    } finally {
      this._testBusy = false;
      this._render();
    }
  }

  async _copyTestUrl() {
    const value = this._testResult?.test_url;
    if (!value) return;
    try {
      await navigator.clipboard.writeText(value);
    } catch (_error) {
      const area = document.createElement("textarea");
      area.value = value;
      area.setAttribute("readonly", "");
      area.style.position = "fixed";
      area.style.opacity = "0";
      this.shadowRoot.append(area);
      area.select();
      document.execCommand("copy");
      area.remove();
    }
    this._testNotice = "NTAG216 test URL copied.";
    this._render();
  }

  _formatTestExpiry(value) {
    const parsed = new Date(value);
    if (!Number.isFinite(parsed.getTime())) return "Unknown";
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(parsed);
  }

  async _copy(value, label) {
    if (!value) return;
    try {
      await navigator.clipboard.writeText(value);
    } catch (_error) {
      const area = document.createElement("textarea");
      area.value = value;
      area.setAttribute("readonly", "");
      area.style.position = "fixed";
      area.style.opacity = "0";
      this.shadowRoot.append(area);
      area.select();
      document.execCommand("copy");
      area.remove();
    }
    this._notice = `${label} copied.`;
    this._render();
  }

  _gototagsProfile() {
    return gototagsProfile(this._result?.ndef_url_template);
  }

  _gototagsCsv() {
    return this._result
      ? buildGoToTagsNtag424Csv(this._result, false, this._permanentlyLock)
      : "";
  }

  _downloadGoToTagsCsv() {
    if (!this._result) return;
    try {
      const blob = new Blob([this._gototagsCsv()], {type: "text/csv;charset=utf-8"});
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      const door = this._doorName.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
      link.href = url;
      link.download = `homepass-${door || "door"}-${this._uid}-gototags.csv`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1_000);
      this._notice = "GoToTags encoding CSV downloaded. Import it into a Variable Encode NFC Tags operation.";
    } catch (error) {
      this._error = error?.message || "HomePASS could not create the GoToTags encoding CSV.";
    }
    this._render();
  }

  _downloadGoToTagsOperation() {
    if (!this._result) return;
    try {
      const name = `HomePASS – ${this._doorName}`;
      const blob = buildGoToTagsNtag424OperationBlob(
        this._result,
        false,
        name,
        this._permanentlyLock,
      );
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      const door = this._doorName.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
      link.href = url;
      link.download = `homepass-${door || "door"}-${this._uid}.gototags`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1_000);
      this._notice = "GoToTags file downloaded. Open it in GoToTags Desktop, click Start encoding, then place the matching tag on the reader after the encoding session starts.";
    } catch (error) {
      this._error = error?.message || "HomePASS could not create the ready-to-write GoToTags file.";
    }
    this._render();
  }

  _downloadPackage() {
    if (!this._result) return;
    const offsets = this._gototagsProfile();
    const payload = {
      schema: "homepass.ntag424-provisioning.v1",
      door: {
        access_point_id: this._result.access_point_id,
        name: this._result.door_name,
      },
      tag: {
        uid_hex: this._result.uid_hex,
        public_id: this._result.public_id,
      },
      ntag424: {
        profile: this._result.profile,
        ndef_url_template: this._result.ndef_url_template,
        meta_read_key: this._result.meta_read_key,
        file_read_key: this._result.file_read_key,
        admin_key: this._result.admin_key,
      },
      encoder_profile: {
        chip_type: "NTAG424",
        ndef_record_type: "WEBSITE",
        cc_access_rights: {
          read: "FREE",
          write: "APP_KEY_0",
          read_write: "APP_KEY_0",
          change: "APP_KEY_0",
        },
        ndef_access_rights: {
          read: "FREE",
          write: "APP_KEY_0",
          read_write: "APP_KEY_0",
          change: "APP_KEY_0",
        },
        sdm: {
          file_read: "APP_KEY_1",
          meta_read: "APP_KEY_2",
          counter_read: "FREE",
          picc_data_offset: offsets.piccData,
          mac_input_offset: offsets.macInput,
          mac_offset: offsets.mac,
          uid_mirroring: true,
          read_counter: true,
          encrypted_file_data: false,
          read_counter_limit: false,
        },
      },
      generated_at: this._result.generated_at,
      warning: "Contains NFC security keys. Store securely and delete after provisioning.",
    };
    const blob = new Blob([`${JSON.stringify(payload, null, 2)}\n`], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const door = this._doorName.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
    link.href = url;
    link.download = `homepass-${door || "door"}-${this._uid}-ntag424.json`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1_000);
    this._notice = "Provisioning package downloaded.";
    this._render();
  }

  _startAnother() {
    this._uid = "";
    this._result = undefined;
    this._permanentlyLock = false;
    this._manualSetup = false;
    this._error = "";
    this._notice = "";
    this._render();
    this.shadowRoot.querySelector("#nfc-tag-uid")?.focus();
  }

  async _confirmProtection() {
    if (this._confirmingProtection || !this._result?.public_id) return;
    if (!globalThis.confirm(
      `GoToTags must show green VERIFIED, one completed tag, and zero errors. Clicking OK records that the ${this._permanentlyLock ? "permanently locked" : "key-protected"} tag setup completed successfully; it does not write to the tag again. Continue?`,
    )) return;
    this._confirmingProtection = true;
    this._error = "";
    this._render();
    try {
      await this._hass.callWS({
        type: "call_service",
        domain: DOMAIN,
        service: CONFIRM_NFC_TAG_PROTECTION_ACTION,
        service_data: {
          access_point_id: this._doorId,
          public_id: this._result.public_id,
        },
        return_response: true,
      });
      this._result.write_protected = true;
      this._notice = this._permanentlyLock
        ? "Tag verified and recorded as permanently locked."
        : "Tag verified and recorded as securely re-writable.";
      this.dispatchEvent(new CustomEvent("homepass-nfc-tag-protected", {
        bubbles: true,
        composed: true,
        detail: {access_point_id: this._doorId},
      }));
    } catch (error) {
      this._error = error?.message || "HomePASS could not record rewrite protection.";
    } finally {
      this._confirmingProtection = false;
      this._render();
    }
  }

  _field(label, value, fieldName, secret = false) {
    return `
      <div class="result-field">
        <div class="result-heading">
          <span>${escapeHtml(label)}</span>
          <button class="copy" type="button" data-copy="${escapeHtml(fieldName)}">Copy</button>
        </div>
        <code class="${secret ? "secret" : ""}">${escapeHtml(value)}</code>
      </div>`;
  }

  _settingsRows(rows) {
    return rows.map(([label, value]) => `
      <div class="manual-setting-row">
        <span>${escapeHtml(label)}</span>
        <code>${escapeHtml(value)}</code>
      </div>`).join("");
  }

  _manualSetupTemplate() {
    if (!this._result || !this._manualSetup) return "";
    const values = goToTagsNtag424Values(
      this._result,
      false,
      this._permanentlyLock,
    );
    const zeroKey = "00000000000000000000000000000000";
    return `
      <section class="manual-setup" aria-labelledby="manual-setup-title">
        <div class="manual-setup-heading">
          <div>
            <h5 id="manual-setup-title">Manual NTAG424 DNA settings</h5>
            <p>Use these values only with software or a writer that supports NXP NTAG424 DNA, AES application keys, NDEF, and Secure Dynamic Messaging.</p>
          </div>
          <button id="close-manual-setup" type="button">Close manual settings</button>
        </div>
        <p class="security-warning"><strong>Enter every value exactly.</strong> Incorrect access rights, keys, or offsets can make the tag unusable. Keep all keys private.</p>
        ${this._field("NDEF website URL", this._result.ndef_url_template, "ndef_url_template")}
        <div class="manual-settings-grid">
          <section>
            <h6>Tag and operation</h6>
            ${this._settingsRows([
              ["Chip", "NXP NTAG424 DNA"],
              ["Tag UID", this._uid],
              ["NDEF record", "WEBSITE"],
              ["Lock after writing", this._permanentlyLock ? "TRUE — permanent and irreversible" : "FALSE — key-protected and re-writable"],
              ["Verify after write", "Enabled"],
              ["Diversified keys", "Unchecked for Keys 0–4"],
            ])}
          </section>
          <section>
            <h6>Application keys</h6>
            ${this._field("New Key 0 — administrator", this._result.admin_key, "admin_key", true)}
            ${this._field("New Key 1 — file read", this._result.file_read_key, "file_read_key", true)}
            ${this._field("New Key 2 — metadata read", this._result.meta_read_key, "meta_read_key", true)}
            ${this._settingsRows([
              ["New Keys 3 and 4", zeroKey],
              ["Current Keys 0–4", zeroKey],
            ])}
          </section>
          <section>
            <h6>CC file access rights</h6>
            ${this._settingsRows([
              ["Read", values["chip.ntag424.files.ccFileAccessRights.readCondition"]],
              ["Write", values["chip.ntag424.files.ccFileAccessRights.writeCondition"]],
              ["Read/Write", values["chip.ntag424.files.ccFileAccessRights.readWriteCondition"]],
              ["Change", values["chip.ntag424.files.ccFileAccessRights.changeCondition"]],
            ])}
          </section>
          <section>
            <h6>NDEF file access rights</h6>
            ${this._settingsRows([
              ["Read", values["chip.ntag424.files.ndefFileAccessRights.readCondition"]],
              ["Write", values["chip.ntag424.files.ndefFileAccessRights.writeCondition"]],
              ["Read/Write", values["chip.ntag424.files.ndefFileAccessRights.readWriteCondition"]],
              ["Change", values["chip.ntag424.files.ndefFileAccessRights.changeCondition"]],
            ])}
          </section>
          <section>
            <h6>Proprietary file access rights</h6>
            ${this._settingsRows([
              ["Read", values["chip.ntag424.files.proprietaryFileAccessRights.readCondition"]],
              ["Write", values["chip.ntag424.files.proprietaryFileAccessRights.writeCondition"]],
              ["Read/Write", values["chip.ntag424.files.proprietaryFileAccessRights.readWriteCondition"]],
              ["Change", values["chip.ntag424.files.proprietaryFileAccessRights.changeCondition"]],
            ])}
          </section>
          <section>
            <h6>Secure Dynamic Messaging</h6>
            ${this._settingsRows([
              ["SDM", "Enabled"],
              ["Encoding", "ASCII"],
              ["File Read", values["chip.ntag424.sdmSettings.accessRights.fileRead"]],
              ["Meta Read", values["chip.ntag424.sdmSettings.accessRights.metaRead"]],
              ["Counter Read", values["chip.ntag424.sdmSettings.accessRights.readCounter"]],
              ["UID Mirroring", "Enabled"],
              ["Read Counter", "Enabled"],
              ["Encrypted File Data", "Disabled"],
              ["Read Counter Limit", "Disabled"],
              ["PICC Data Offset", values["chip.ntag424.sdmSettings.offsets.piccData"]],
              ["MAC Input Offset", values["chip.ntag424.sdmSettings.offsets.macInput"]],
              ["MAC Offset", values["chip.ntag424.sdmSettings.offsets.mac"]],
            ])}
          </section>
        </div>
      </section>`;
  }

  _resultTemplate() {
    if (!this._result) return "";
    return `
      <section class="result" aria-labelledby="nfc-result-title">
        <div class="result-title">
          <div>
            <h5 id="nfc-result-title">Ready to write</h5>
            <p>Tag UID <code>${escapeHtml(this._uid)}</code> is now assigned to ${escapeHtml(this._doorName)}.</p>
          </div>
          <span class="ready">Prepared</span>
        </div>
        <p class="helper">Choose the automatic GoToTags file or enter the complete settings into another NTAG424-compatible writer.</p>
        <div class="result-actions">
          <button class="primary" id="download-gototags-operation" type="button">Download GoToTags file</button>
          <button id="show-manual-setup" type="button">Set up tag manually</button>
          ${this._result.write_protected ? `<button id="prepare-another-tag" type="button">Prepare another tag</button>` : ""}
        </div>
        <div class="write-steps guided-setup">
          <div class="guided-heading">
            <div>
              <h5>Automatic setup with GoToTags Desktop</h5>
              <p>The downloaded file opens directly in the correct NFC tag operation.</p>
            </div>
            <span class="time-guide">Recommended</span>
          </div>
          <ol class="guided-list">
            <li>
              <div><strong>Open the downloaded file</strong><span class="screen-name">GoToTags Desktop</span></div>
              <p>Double-click the <strong>.gototags</strong> file. GoToTags Desktop opens automatically in the appropriate NFC tag operation.</p>
            </li>
            <li>
              <div><strong>Start encoding</strong><span class="screen-name">GoToTags Desktop</span></div>
              <p>Confirm the operation shows one <strong>READY</strong> row and <strong>Lock ${this._permanentlyLock ? "TRUE" : "FALSE"}</strong>, then click <strong>Start encoding</strong>.</p>
            </li>
            <li>
              <div><strong>Place the tag on the reader</strong><span class="screen-name">Reader</span></div>
              <p>Once the encoding session has started, place only tag UID <code>${escapeHtml(this._uid)}</code> on the reader. Encoding and verification complete automatically.</p>
            </li>
            <li>
              <div><strong>Verify and test</strong><span class="screen-name">Result</span></div>
              <p>Wait for green <strong>VERIFIED</strong>, one completed tag, and zero errors. Remove the tag and tap it with a phone. Confirm the page names and unlocks ${escapeHtml(this._doorName)}.</p>
            </li>
          </ol>
          <details class="setup-recovery">
            <summary>If GoToTags reports an error</summary>
            <ul>
              <li>Pause the operation and remove the tag. Do not repeatedly press Play.</li>
              <li>If the reader was disconnected, reconnect it before restarting GoToTags.</li>
              <li>Inspect the tag in <strong>NFC Tag Tools</strong> before retrying because some keys may already have changed.</li>
              <li>${this._permanentlyLock ? "A permanently locked tag cannot be repaired or re-encoded. Set it aside if verification fails." : "This tag remains key-protected and can be re-encoded later with its HomePASS administrator key."}</li>
              <li>If GoToTags says the tag is corrupted or the access rights are invalid, set that tag aside rather than risking another write.</li>
            </ul>
          </details>
        </div>
        ${this._manualSetupTemplate()}
        <div class="verification-confirmation">
          <h5>Finish in HomePASS</h5>
          <p>After GoToTags reports green <strong>VERIFIED</strong>, one completed tag, and zero errors, record the completed setup in HomePASS. This button does not write to the tag again.</p>
          <button class="primary" id="confirm-nfc-protection" type="button" ${this._result.write_protected || this._confirmingProtection ? "disabled" : ""}>${this._result.write_protected ? "Tag setup recorded" : this._confirmingProtection ? "Recording…" : "Record completed tag setup"}</button>
        </div>
        <p class="security-warning"><strong>Keep the file private.</strong> The download contains this tag's door security keys. Do not share it; delete it after the tag has been written and verified.</p>
      </section>`;
  }

  _testTagTemplate() {
    const active = this._testStatus?.active === true;
    const expiry = active ? this._formatTestExpiry(this._testStatus.expires_at) : "";
    return `
      <section class="card test-card" aria-labelledby="nfc-test-title">
        <div class="intro">
          <div class="nfc-mark test-mark" aria-hidden="true">
            <svg viewBox="0 0 28 28" role="presentation">
              <circle cx="6" cy="14" r="1.6" fill="currentColor"></circle>
              <path d="M9 10.5c4 1.9 4 5.1 0 7" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"></path>
              <path d="M12 7.5c7 3.5 7 9.5 0 13" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"></path>
              <path d="M15 4.5c10 5.2 10 13.8 0 19" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"></path>
            </svg>
          </div>
          <div>
            <div class="title-with-badge">
              <h4 id="nfc-test-title">Test now with NTAG216</h4>
              <span class="test-badge">Temporary</span>
            </div>
            <p>Use a static Nabu Casa URL to test enrollment, Face ID, authorization, and a real unlock of ${escapeHtml(this._doorName)}.</p>
          </div>
        </div>
        <p class="security-warning"><strong>Testing only.</strong> NTAG216 cannot prove that the physical tag is genuine, so its URL can be copied. Revoke it after testing and use NTAG424 DNA for permanent installation.</p>
        ${this._testLoading ? `<p class="helper" role="status">Checking test-tag status…</p>` : ""}
        ${!this._testLoading && !active ? `
          <div class="prepare-row">
            <button class="primary" id="create-nfc-test-tag" type="button" ${this._testBusy ? "disabled" : ""}>${this._testBusy ? "Creating…" : "Create 7-day test URL"}</button>
            <span class="helper">Creating a new URL revokes any older NTAG216 test URL for this door.</span>
          </div>` : ""}
        ${active ? `
          <div class="test-status">
            <div><strong>Test tag active</strong><span>Expires ${escapeHtml(expiry)}</span></div>
            <button class="danger" id="revoke-nfc-test-tag" type="button" ${this._testBusy ? "disabled" : ""}>${this._testBusy ? "Working…" : "Revoke test tag"}</button>
          </div>` : ""}
        ${this._testResult ? `
          <section class="test-result" aria-labelledby="nfc-test-url-title">
            <div class="result-heading"><span id="nfc-test-url-title">Nabu Casa URL to write</span></div>
            <code>${escapeHtml(this._testResult.test_url)}</code>
            <div class="result-actions">
              <button class="primary" id="copy-nfc-test-url" type="button">Copy URL</button>
              <a class="button-link" href="${escapeHtml(this._testResult.test_url)}" target="_blank" rel="noopener noreferrer">Open test page</a>
            </div>
            ${this._testResult.qr_code ? `<img class="test-qr" src="${escapeHtml(this._testResult.qr_code)}" alt="QR code for the NTAG216 test URL" />` : ""}
            <div class="write-steps">
              <h5>Write the NTAG216</h5>
              <ol>
                <li>Copy the Nabu Casa URL above.</li>
                <li>In your NFC writing software, add it as a URL or URI NDEF record.</li>
                <li>Write the record to the NTAG216. Do not permanently lock the test tag.</li>
                <li>Tap it with the enrolled user's phone and complete Face ID.</li>
              </ol>
            </div>
          </section>` : active ? `<p class="helper">The URL is only displayed when it is created. The written tag remains usable until the expiry above or until you revoke it.</p>` : ""}
        ${this._testError ? `<p class="message error" role="alert">${escapeHtml(this._testError)}</p>` : ""}
        ${this._testNotice ? `<p class="message notice" role="status">${escapeHtml(this._testNotice)}</p>` : ""}
      </section>`;
  }

  _render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: grid; gap: 16px; color: var(--primary-text-color); }
        * { box-sizing: border-box; }
        .card { display: grid; gap: 14px; padding: 16px; border: 1px solid var(--divider-color); border-radius: 14px; background: color-mix(in srgb, var(--primary-color) 5%, var(--card-background-color)); }
        .intro { display: flex; gap: 12px; align-items: flex-start; }
        .nfc-mark { display: grid; place-items: center; flex: 0 0 42px; width: 42px; height: 42px; border-radius: 12px; color: var(--primary-color); background: color-mix(in srgb, var(--primary-color) 12%, transparent); }
        .nfc-mark svg { width: 26px; height: 26px; overflow: visible; }
        .test-card { border-color: color-mix(in srgb, var(--warning-color, #a66300) 28%, var(--divider-color)); background: color-mix(in srgb, var(--warning-color, #f0a000) 5%, var(--card-background-color)); }
        .test-mark { color: var(--warning-color, #a66300); background: color-mix(in srgb, var(--warning-color, #f0a000) 13%, transparent); }
        .title-with-badge { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
        .test-badge { padding: 3px 8px; border-radius: 999px; color: var(--warning-color, #8a5700); background: color-mix(in srgb, var(--warning-color, #f0a000) 14%, transparent); font-size: 11px; font-weight: 800; text-transform: uppercase; }
        h4, h5, p { margin: 0; }
        h4 { font-size: 17px; }
        h5 { font-size: 15px; }
        .intro p, .helper, .result p { color: var(--secondary-text-color); line-height: 1.45; }
        label { display: grid; gap: 6px; font-weight: 650; }
        a { color: var(--primary-color); }
        input { width: 100%; min-height: 44px; padding: 10px 12px; border: 1px solid var(--divider-color); border-radius: 10px; background: var(--card-background-color); color: var(--primary-text-color); font: 600 15px ui-monospace, SFMono-Regular, Menlo, monospace; text-transform: uppercase; }
        input:focus { outline: 2px solid var(--primary-color); outline-offset: 1px; }
        button, .button-link { display: inline-flex; min-height: 40px; padding: 9px 14px; align-items: center; justify-content: center; border: 1px solid var(--divider-color); border-radius: 999px; background: var(--card-background-color); color: var(--primary-text-color); font: inherit; font-weight: 650; text-decoration: none; cursor: pointer; }
        button.primary { border-color: var(--primary-color); background: var(--primary-color); color: var(--text-primary-color, #fff); }
        button.danger { border-color: color-mix(in srgb, var(--error-color) 32%, var(--divider-color)); color: var(--error-color); }
        button:disabled { cursor: default; opacity: .55; }
        .prepare-row, .result-actions { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
        fieldset { display: grid; gap: 10px; margin: 0; padding: 13px; border: 1px solid var(--divider-color); border-radius: 12px; }
        legend { padding: 0 6px; font-weight: 750; }
        .write-choice { display: grid; grid-template-columns: 20px 1fr; gap: 3px 9px; align-items: start; padding: 10px; border: 1px solid var(--divider-color); border-radius: 10px; background: var(--card-background-color); cursor: pointer; }
        .write-choice input { width: 18px; min-height: 18px; margin: 2px 0 0; padding: 0; accent-color: var(--primary-color); }
        .write-choice strong { line-height: 1.35; }
        .write-choice span { grid-column: 2; color: var(--secondary-text-color); font-size: 13px; font-weight: 400; line-height: 1.4; }
        .message { padding: 10px 12px; border-radius: 10px; line-height: 1.4; }
        .message.error { color: var(--error-color); background: color-mix(in srgb, var(--error-color) 10%, transparent); }
        .message.notice { color: var(--success-color, #2e7d32); background: color-mix(in srgb, var(--success-color, #2e7d32) 10%, transparent); }
        .result { display: grid; gap: 12px; padding-top: 14px; border-top: 1px solid var(--divider-color); }
        .test-result { display: grid; gap: 12px; }
        .test-status { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 12px; align-items: center; padding: 12px; border-radius: 10px; background: var(--secondary-background-color); }
        .test-status > div { display: grid; gap: 2px; }
        .test-status span { color: var(--secondary-text-color); font-size: 13px; }
        .test-qr { width: min(100%, 260px); height: auto; padding: 10px; justify-self: center; border-radius: 12px; background: #fff; }
        .result-title { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; }
        .ready { padding: 4px 9px; border-radius: 999px; color: var(--success-color, #2e7d32); background: color-mix(in srgb, var(--success-color, #2e7d32) 12%, transparent); font-size: 12px; font-weight: 750; }
        .result-field { display: grid; gap: 6px; }
        .result-heading { display: flex; justify-content: space-between; gap: 10px; align-items: center; font-size: 13px; font-weight: 700; }
        .copy { min-height: 32px; padding: 5px 11px; font-size: 12px; }
        code { display: block; overflow-wrap: anywhere; padding: 10px; border-radius: 9px; background: var(--secondary-background-color); color: var(--primary-text-color); font: 12px/1.45 ui-monospace, SFMono-Regular, Menlo, monospace; }
        code.secret { letter-spacing: .035em; }
        .write-steps { display: grid; gap: 10px; padding: 14px; border-radius: 12px; background: var(--secondary-background-color); }
        .guided-heading { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; }
        .guided-heading > div { display: grid; gap: 4px; }
        .guided-heading p, .guided-list p { color: var(--secondary-text-color); line-height: 1.45; }
        .time-guide, .screen-name { display: inline-flex; width: fit-content; padding: 3px 8px; border-radius: 999px; color: var(--primary-color); background: color-mix(in srgb, var(--primary-color) 10%, transparent); font-size: 11px; font-weight: 700; }
        .guided-list { counter-reset: setup-step; list-style: none; gap: 14px; padding: 0; }
        .guided-list > li { counter-increment: setup-step; position: relative; display: grid; gap: 7px; min-height: 34px; padding-left: 44px; }
        .guided-list > li::before { content: counter(setup-step); position: absolute; top: 0; left: 0; display: grid; place-items: center; width: 32px; height: 32px; border-radius: 50%; color: var(--text-primary-color, #fff); background: var(--primary-color); font-weight: 800; }
        .guided-list > li > div { display: flex; flex-wrap: wrap; gap: 7px; align-items: center; }
        .guided-list ul, .setup-recovery ul { display: grid; gap: 6px; margin: 0; padding-left: 20px; line-height: 1.4; }
        .setup-recovery { padding: 10px 12px; border: 1px solid var(--divider-color); border-radius: 10px; background: var(--card-background-color); }
        .setup-recovery summary { cursor: pointer; font-weight: 700; }
        .setup-recovery[open] summary { margin-bottom: 10px; }
        .verification-confirmation { display: grid; gap: 9px; padding: 12px; border: 1px solid color-mix(in srgb, var(--success-color, #2e7d32) 30%, var(--divider-color)); border-radius: 10px; }
        .verification-confirmation p { color: var(--secondary-text-color); line-height: 1.4; }
        .manual-setup { display: grid; gap: 14px; padding: 14px; border: 1px solid var(--primary-color); border-radius: 12px; background: var(--card-background-color); }
        .manual-setup-heading { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; }
        .manual-setup-heading > div { display: grid; gap: 4px; }
        .manual-setup-heading p { color: var(--secondary-text-color); line-height: 1.4; }
        .manual-settings-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; }
        .manual-settings-grid > section { display: grid; align-content: start; gap: 8px; padding: 12px; border: 1px solid var(--divider-color); border-radius: 10px; }
        h6 { margin: 0; font-size: 14px; }
        .manual-setting-row { display: grid; gap: 4px; }
        .manual-setting-row > span { color: var(--secondary-text-color); font-size: 12px; font-weight: 700; }
        ol { display: grid; gap: 7px; margin: 0; padding-left: 22px; line-height: 1.4; }
        .security-warning { padding: 10px 12px; border-radius: 10px; color: var(--warning-color, #8a5700); background: color-mix(in srgb, var(--warning-color, #f0a000) 12%, transparent); }
        @media (max-width: 520px) { .result-title, .guided-heading, .manual-setup-heading { display: grid; } .ready, .time-guide { justify-self: start; } }
      </style>
      <section class="card" aria-labelledby="nfc-provision-title">
        <div class="intro">
          <div class="nfc-mark" aria-hidden="true">
            <svg viewBox="0 0 28 28" role="presentation">
              <circle cx="6" cy="14" r="1.6" fill="currentColor"></circle>
              <path d="M9 10.5c4 1.9 4 5.1 0 7" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"></path>
              <path d="M12 7.5c7 3.5 7 9.5 0 13" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"></path>
              <path d="M15 4.5c10 5.2 10 13.8 0 19" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"></path>
            </svg>
          </div>
          <div>
            <h4 id="nfc-provision-title">Prepare NFC tag</h4>
            <p><strong>Only genuine NTAG424 DNA tags are supported by HomePASS.</strong></p>
          </div>
        </div>
        <p class="helper">For the simplest setup, install <a href="https://gototags.com/software" target="_blank" rel="noopener noreferrer">GoToTags Desktop software</a> and use an NTAG424 DNA-compatible reader/writer such as the <strong>ACS ACR1552U USB-C NFC Reader IV</strong>. Other NTAG424-compatible writers and software can also be used; choose <strong>Set up tag manually</strong> after creating the setup.</p>
        <p class="helper">Enter the tag's 14-digit UID below. This may have been provided with the tag or can be read using most NFC readers.</p>
        <label for="nfc-tag-uid">
          Tag UID
          <input id="nfc-tag-uid" value="${escapeHtml(this._uid)}" inputmode="text" autocomplete="off" spellcheck="false" maxlength="14" placeholder="14 hexadecimal characters" ${this._busy ? "disabled" : ""} />
        </label>
        <fieldset ${this._busy ? "disabled" : ""}>
          <legend>After writing the tag</legend>
          <label class="write-choice">
            <input type="radio" name="tag-lock-mode" value="rewritable" ${this._permanentlyLock ? "" : "checked"} />
            <strong>Leave it re-writable with the HomePASS administrator key (recommended)</strong>
            <span>The tag cannot be rewritten without its private key, but an administrator can intentionally update or recover it later.</span>
          </label>
          <label class="write-choice">
            <input type="radio" name="tag-lock-mode" value="permanent" ${this._permanentlyLock ? "checked" : ""} />
            <strong>Lock it as permanently written</strong>
            <span>This gives the strongest protection against alteration, but it is irreversible. If the URL or setup is wrong or later changes, the tag must be replaced.</span>
          </label>
        </fieldset>
        <div class="prepare-row">
          <button class="primary" id="prepare-nfc-tag" type="button" ${!this._validUid() || this._busy || !this._doorId ? "disabled" : ""}>${this._busy ? "Preparing…" : "Create tag setup"}</button>
          <span class="helper">One package is created for one physical tag and one door.</span>
        </div>
        ${this._error ? `<p class="message error" role="alert">${escapeHtml(this._error)}</p>` : ""}
        ${this._notice ? `<p class="message notice" role="status">${escapeHtml(this._notice)}</p>` : ""}
        ${this._resultTemplate()}
      </section>`;

    const input = this.shadowRoot.querySelector("#nfc-tag-uid");
    input?.addEventListener("input", () => {
      this._uid = this._normalizedUid(input.value);
      input.value = this._uid;
      const prepare = this.shadowRoot.querySelector("#prepare-nfc-tag");
      if (prepare) prepare.disabled = !this._validUid() || this._busy || !this._doorId;
    });
    this.shadowRoot.querySelectorAll('input[name="tag-lock-mode"]').forEach((choice) => {
      choice.addEventListener("change", () => {
        this._permanentlyLock = choice.value === "permanent";
        this._manualSetup = false;
        this._render();
      });
    });
    this.shadowRoot.querySelector("#prepare-nfc-tag")?.addEventListener("click", () => this._prepareTag());
    this.shadowRoot.querySelector("#create-nfc-test-tag")?.addEventListener("click", () => this._createTestTag());
    this.shadowRoot.querySelector("#revoke-nfc-test-tag")?.addEventListener("click", () => this._revokeTestTag());
    this.shadowRoot.querySelector("#copy-nfc-test-url")?.addEventListener("click", () => this._copyTestUrl());
    this.shadowRoot.querySelector("#download-gototags-operation")?.addEventListener("click", () => this._downloadGoToTagsOperation());
    this.shadowRoot.querySelector("#show-manual-setup")?.addEventListener("click", () => {
      this._manualSetup = true;
      this._render();
      this.shadowRoot.querySelector("#manual-setup-title")?.scrollIntoView({block: "start"});
    });
    this.shadowRoot.querySelector("#close-manual-setup")?.addEventListener("click", () => {
      this._manualSetup = false;
      this._render();
    });
    this.shadowRoot.querySelector("#download-gototags-csv")?.addEventListener("click", () => this._downloadGoToTagsCsv());
    this.shadowRoot.querySelector("#download-nfc-package")?.addEventListener("click", () => this._downloadPackage());
    this.shadowRoot.querySelector("#prepare-another-tag")?.addEventListener("click", () => this._startAnother());
    this.shadowRoot.querySelector("#confirm-nfc-protection")?.addEventListener("click", () => this._confirmProtection());
    this.shadowRoot.querySelectorAll("[data-copy]").forEach((button) => {
      button.addEventListener("click", () => {
        const field = button.dataset.copy;
        const labels = {
          ndef_url_template: "NDEF URL template",
          meta_read_key: "Meta Read key",
          file_read_key: "File Read key",
          admin_key: "Administrator rewrite key",
          profile: "SDM profile",
        };
        void this._copy(this._result?.[field], labels[field] || "Value");
      });
    });
  }
}
