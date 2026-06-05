<template lang="pug">
  v-container(fluid)
    v-row
      v-col(cols="12" md="10" lg="8" class="mx-auto")
        h1 Privacy notice

        p
          | This site uses
          |
          a(href="https://umami.is" target="_blank" rel="noopener noreferrer") Umami
          | , a privacy-focused, open-source web analytics tool. Umami does not use cookies, does not collect personally
          | identifiable information, and does not track users across sites or sessions.

        h2 What we collect

        v-list(lines="1")
          v-list-item
            strong Page views and referrer URLs
            |  — to understand which pages are visited and where visitors come from.
          v-list-item
            strong Browser and device type
            |  — aggregated, to help optimise the interface.
          v-list-item
            strong Country-level location
            |  — derived from the IP address, which is not stored.

        h2 What we do not collect

        v-list(lines="1")
          v-list-item No cookies are set.
          v-list-item No personal data or identifiers are stored.
          v-list-item No cross-site tracking is performed.
          v-list-item IP addresses are not retained.

        h2 Data storage

        p
          | Analytics data is processed by a self-hosted Umami instance operated by CompOmics at Ghent University / VIB.
          | Data are not shared with third parties.

</template>
