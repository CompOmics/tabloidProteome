<script setup lang="ts">
import { ref } from "vue";

// Base64 encoded email addresses
const emails = ref<string[]>([
    "TGVubmFydC5NYXJ0ZW5zQFVHZW50LmJl", // Lennart.Martens@UGent.be
    "TmF0YWxpYS5UaWNoc2hlbmtvQFVHZW50LmJl", // Natalia.Tichshenko@UGent.be
    "RW5yaWNvLk1hc3NpZ25hbmlAVUdlbnQuYmU=", // Enrico.Massignani@UGent.be
]);

const decodeEmail = (encoded: string): string => {
    try {
        return atob(encoded);
    } catch (e) {
        console.error("Failed to decode email", e);
        return "";
    }
};

const displayEmail = (encoded: string): string => {
    return decodeEmail(encoded);
};
</script>

<template lang="pug">
  v-container(fluid)
    v-row
      v-col(cols="12" md="10" lg="8" class="mx-auto")
        h1 About
        p
          | Biological systems are organized as networks of interacting and co-regulated entities. While many resources focus on
          | direct physical protein–protein interactions, a large fraction of biologically meaningful relationships reflects
          em functional association
          | (e.g., shared pathway membership, coordinated regulation, complex co-membership, or
          | context-specific co-activity). Detecting such associations at scale remains challenging.
    v-row
      v-col(cols="12" md="10" lg="8" class="mx-auto")
        h2 Tabloid Proteome

        p
          | The 
          strong online Tabloid Proteome 
          | is a knowledgebase of protein functional associations inferred from the
          br
          strong co-occurrence of proteins across large collections of public, mass spectrometry-based proteomics datasets
          | . This strategy provides information that is complementary to traditional direct interaction assays by capturing broader
          | functional relationships that repeatedly manifest across many independent experiments.

        p
          | In the original implementation, public proteomics experiments from PRIDE were reprocessed in a uniform pipeline, and
          | protein–protein associations were derived from co-occurrence patterns using a Jaccard-style similarity defined on
          | identification evidence across experiments. The resulting association network is presented through a web interface
          | that supports interactive exploration and filtering.
    v-row
      v-col(cols="12" md="10" lg="8" class="mx-auto")
        h2 MoDPA: modification-dependent protein associations

        p
          | Our approach has been expanded to account for post-translational modifications (PTMs) by introducing
          br
          strong MoDPA (Modification-Dependent Protein Associations)
          | , a resource that captures functional associations
          | between 
          strong co-occurring modified residues
          | . Whereas Tabloid Proteome operates primarily at the protein level,
          | MoDPA adds a mechanistic layer by representing relationships between specific PTM sites.

        p
          | In MoDPA, the network is represented as follows:
        v-list(lines="1")
          v-list-item
            strong Nodes 
            | represent PTMs on specific protein residues (i.e., a modification type localized to a site).
          v-list-item
            strong Edges 
            | represent consistent co-occurrence and dependency patterns between PTM sites across runs and projects.
          v-list-item
            strong Edge weights 
            | quantify the strength (and, where relevant, direction) of association between PTM sites.
        //- ul

        //-   li
        //-     strong Nodes 
        //-     | represent PTMs on specific protein residues (i.e., a modification type localized to a site).
        //-   li
        //-     strong Edges 
        //-     | represent consistent co-occurrence and dependency patterns between PTM sites across runs and projects.
        //-   li
        //-     strong Edge weights 
        //-     | quantify the strength (and, where relevant, direction) of association between PTM sites.

        p
          | Briefly, PTM abundance profiles across runs are first projected into a low-dimensional latent space using a
          br
          strong Variational Autoencoder (VAE)
          | . Associations are then quantified between PTM sites in that latent space,
          | using a dependency measure designed to capture non-linear relationships; in our current implementation, this is based
          | on 
          strong signed distance correlation
          | computed between latent representations. This design is motivated by
          | VAE-based functional association frameworks and by the use of signed distance correlation for robust network
          | construction in high-dimensional biological settings.

        p
          strong Current scale.
          | In total, we have re-analyzed 
          strong 633 PRIDE projects
          | comprising
          br
          strong 36,651 raw files
          | . The resulting MoDPA network enables downstream analyses such as community detection,
          | functional enrichment, and contextual interpretation via protein-level knowledge.
    v-row
      v-col(cols="12" md="10" lg="8" class="mx-auto")
        h2 Recommended citation
        p
          | MoDPA is an ongoing extension that builds on the Tabloid Proteome concept; citation details for MoDPA will be provided
          | here as soon as the corresponding manuscript is available.
    v-row
      v-col(cols="12" md="10" lg="8" class="mx-auto")
        h2 Funding and development

        p
          | Tabloid Proteome is developed at Ghent University / VIB-UGent Center for Medical Biotechnology and is listed as an
          | ELIXIR Belgium service. Relevant funding acknowledgements and service context are provided through ELIXIR Belgium.
    v-row
      v-col(cols="12" md="10" lg="8" class="mx-auto")
        h2 Useful links

        p Github repository:
          a(:href="'https://github.com/CompOmics/tabloidProteome/tree/modpa'" target="_blank")
            | https://github.com/CompOmics/tabloidProteome/tree/modpa
        p MoDPA reproducible methodology Github repository:
          a(:href="'https://github.com/CompOmics/MoDPAv1.0'" target="_blank")
            | https://github.com/CompOmics/MoDPAv1.0

        p Article preprint:
          a(:href="'https://www.biorxiv.org/content/10.64898/2026.01.20.700550v1'" target="_blank")
            | MoDPA: Inferring Modification-dependent Protein Associations from Uniformly Reprocessed Mass Spectrometry
          
    v-row
      v-col(cols="12" md="10" lg="8" class="mx-auto")
        h2 Contact
        v-list(lines="1")
          v-list-item
            a(:href="'mailto:' + decodeEmail(emails[0])" :data-email="emails[0]")
              | {{ displayEmail(emails[0]) }}
          v-list-item
            a(:href="'mailto:' + decodeEmail(emails[1])" :data-email="emails[1]")
              | {{ displayEmail(emails[1]) }}
          v-list-item
            a(:href="'mailto:' + decodeEmail(emails[2])" :data-email="emails[2]")
              | {{ displayEmail(emails[2]) }}

</template>

<style>
@media (min-width: 1024px) {
    .about {
        min-height: 100vh;
        display: flex;
        align-items: center;
    }
}
</style>
