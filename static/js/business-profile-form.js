document.addEventListener("DOMContentLoaded", () => {
  const typeSelect = document.querySelector("[data-business-profile-type]");
  const categorySelect = document.querySelector("[data-organization-category]");
  const categoryFields = document.querySelectorAll("[data-organization-field]");
  const ownerPrivacy = document.querySelector("[data-owner-privacy]");
  const ownerContactPrivacy = document.querySelectorAll("[data-owner-contact-privacy]");
  const identityPrivacyDescription = document.querySelector("[data-identity-privacy-description]");
  if (!typeSelect) return;

  const setText = (selector, text) => {
    document.querySelectorAll(selector).forEach((element) => { element.textContent = text; });
  };

  const update = () => {
    const isOrganization = typeSelect.value === "ORGANIZATION";
    const isEducation = isOrganization && categorySelect?.value === "EDUCATIONAL_INSTITUTE";
    const profileTerm = isOrganization ? "Organization" : "Business";
    const offeringHeading = isEducation ? "Academic Programs" : (isOrganization ? "Products & Services" : "Featured Products & Services");
    const itemTerm = isEducation ? "Academic Program" : "Product / Service";

    categoryFields.forEach((field) => { field.hidden = !isOrganization; });
    if (ownerPrivacy) ownerPrivacy.hidden = false;
    ownerContactPrivacy.forEach((field) => { field.hidden = isOrganization; });
    if (identityPrivacyDescription) {
      identityPrivacyDescription.textContent = isOrganization
        ? "Choose whether the representative assigned to this card appears above your organization details."
        : "Choose whether the owner or assigned representative appears above your business details. Multiple-card pages use only each card’s assigned representative.";
    }

    const labels = {
      eyebrow: isOrganization ? "Organization identity" : "Business identity",
      edit_title: `Edit ${profileTerm} Profile`,
      edit_description: `Manage your ${profileTerm.toLowerCase()} information and online presence.`,
      preview_link: `Preview ${profileTerm} Profile`,
      name_label: `${profileTerm} Name`,
      logo_label: `${profileTerm} Logo`,
      banner_label: "Organization Cover Image (optional)",
      description_label: `${profileTerm} Description`,
      contact_heading: `${profileTerm} Contact Information`,
      phone_label: `${profileTerm} Phone`,
      email_label: `${profileTerm} Email`,
      website_label: `${profileTerm} Website`,
      address_label: `${profileTerm} Address`,
      offerings_heading: offeringHeading,
      offerings_description: isEducation
        ? "Add up to six academic programs to highlight on your profile."
        : `Add up to six products or services to highlight on your ${isOrganization ? "organization" : "business"} profile.`,
      offering_legend: itemTerm,
      offering_error_prefix: itemTerm,
      save_button: `Save ${profileTerm} Profile`,
      save_preview_button: `Save & Preview ${profileTerm} Profile`,
    };
    Object.entries(labels).forEach(([key, value]) => {
      setText(`[data-dynamic-label="${key}"]`, value);
    });

    const offeringLabels = isEducation
      ? { name: "Program Name", description: "Program Details", external_url: "Program Website / Learn More" }
      : { name: "Product / Service Name", description: "Description / Details", external_url: "More Information Link" };
    Object.entries(offeringLabels).forEach(([key, value]) => {
      setText(`[data-dynamic-offering-label="${key}"]`, value);
    });
    const nameInput = document.getElementById("id_name");
    const descriptionInput = document.getElementById("id_description");
    const websiteInput = document.getElementById("id_website");
    if (nameInput) nameInput.placeholder = isOrganization ? "Organization or institute name" : "e.g. AR Kitchen";
    if (descriptionInput) descriptionInput.placeholder = isOrganization
      ? "A short introduction to your organization"
      : "A short introduction to your business and what you offer";
    if (websiteInput) websiteInput.placeholder = isOrganization ? "yourorganization.com" : "yourbusiness.com";
    document.title = `${labels.edit_title} · NexTap`;
  };

  typeSelect.addEventListener("change", update);
  categorySelect?.addEventListener("change", update);
  update();
});
