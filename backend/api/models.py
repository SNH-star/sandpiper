"""
models.py
- Data classes for SingleM databases
"""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

db = SQLAlchemy()

class Marker(db.Model):
    __tablename__ = 'markers'
    id = db.Column(db.Integer, server_default=text("nextval('markers_id_seq')"), primary_key=True)
    marker = db.Column(db.String, nullable=False)

    def to_dict(self):
        return dict(id=self.id,
                    marker=self.marker)

class Nucleotide(db.Model):
    __tablename__ = 'nucleotides'
    id = db.Column(db.Integer, server_default=text("nextval('nucleotides_id_seq')"), primary_key=True)
    marker_id = db.Column(db.Integer, db.ForeignKey('markers.id'), nullable=False)
    sequence = db.Column(db.String, nullable=False)
    marker_wise_id = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return dict(id=self.id,
                    marker_id=self.marker_id,
                    sequence=self.sequence,
                    marker_wise_id=self.marker_wise_id)

class CondensedProfile(db.Model):
    __tablename__ = 'condensed_profiles'
    #     "CREATE TABLE condensed_profiles (id INTEGER PRIMARY KEY,"
    #     " sample_name text, coverage float, taxonomy_id INTEGER);\n")
    id = db.Column(db.Integer, server_default=text("nextval('condensed_profiles_id_seq')"), primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey('ncbi_metadata.id'), nullable=False, index=True)
    coverage = db.Column(db.Float, nullable=False, index=True)
    filled_coverage = db.Column(db.Float, nullable=False, index=True)
    # relative_abundance is a filled coverage
    relative_abundance = db.Column(db.Float, nullable=False, index=True)
    taxonomy_id = db.Column(db.Integer, db.ForeignKey('taxonomies.id'), nullable=False, index=True)
    taxonomy_type = db.Column(db.String, nullable=False, index=True)

    # domain_id = db.Column(db.Integer, db.ForeignKey('taxonomies.id'), index=True)
    # phylum_id = db.Column(db.Integer, db.ForeignKey('taxonomies.id'), index=True)
    # class_id = db.Column(db.Integer, db.ForeignKey('taxonomies.id'), index=True)
    # order_id = db.Column(db.Integer, db.ForeignKey('taxonomies.id'), index=True)
    # family_id = db.Column(db.Integer, db.ForeignKey('taxonomies.id'), index=True)
    # genus_id = db.Column(db.Integer, db.ForeignKey('taxonomies.id'), index=True)
    # species_id = db.Column(db.Integer, db.ForeignKey('taxonomies.id'), index=True)

    ncbi_metadata = db.relationship("NcbiMetadata", back_populates="condensed_profiles")
    taxonomy = db.relationship("Taxonomy", back_populates="condensed_profiles", foreign_keys=[taxonomy_id])


class CondensedProfileCtas1(db.Model):
    '''Materialized subset of CondensedProfile for taxonomy search performance.'''
    __tablename__ = 'condensed_profiles_ctas1'
    taxonomy_id = db.Column(db.Integer, db.ForeignKey('taxonomies.id'), primary_key=True, index=True)
    run_id = db.Column(db.Integer, db.ForeignKey('ncbi_metadata.id'), primary_key=True, index=True)
    relative_abundance = db.Column(db.Float, nullable=False, index=True)
    filled_coverage = db.Column(db.Float, nullable=False, index=True)


class Taxonomy(db.Model):
    # Not used here but this is the logical place to put it since it is used in the condensed profile
    # taxonomy_level_columns = ['domain_id','phylum_id','class_id','order_id','family_id','genus_id','species_id']

    #     "CREATE TABLE taxonomies (id INTEGER PRIMARY KEY, taxonomy_level TEXT, parent_id INTEGER, name TEXT); \n"
    __tablename__ = 'taxonomies'
    id = db.Column(db.Integer, server_default=text("nextval('taxonomies_id_seq')"), primary_key=True)
    taxonomy_level = db.Column(db.String, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('taxonomies.id'), nullable=True)
    name = db.Column(db.String, nullable=False, index=True)
    full_name = db.Column(db.String, nullable=False)
    taxonomy_type = db.Column(db.String, nullable=False, index=True)
    host_sample_count = db.Column(db.Integer)
    ecological_sample_count = db.Column(db.Integer)

    condensed_profiles = db.relationship('CondensedProfile', back_populates='taxonomy', foreign_keys=[CondensedProfile.taxonomy_id])
    # condensed_profile_domains = db.relationship('CondensedProfile', foreign_keys=[CondensedProfile.domain_id])
    # condensed_profile_phyla = db.relationship('CondensedProfile', foreign_keys=[CondensedProfile.phylum_id])
    # condensed_profile_classes = db.relationship('CondensedProfile', foreign_keys=[CondensedProfile.class_id])
    # condensed_profile_orders = db.relationship('CondensedProfile', foreign_keys=[CondensedProfile.order_id])
    # condensed_profile_families = db.relationship('CondensedProfile', foreign_keys=[CondensedProfile.family_id])
    # condensed_profile_genera = db.relationship('CondensedProfile', foreign_keys=[CondensedProfile.genus_id])
    # condensed_profile_species = db.relationship('CondensedProfile', foreign_keys=[CondensedProfile.species_id])

    def to_dict(self):
        return dict(id=self.id,
                    taxonomy_level=self.taxonomy_level,
                    parent_id=self.parent_id,
                    name=self.name)

    def split_taxonomy(self):
        return self.full_name.split('; ')

class BiosampleAttribute(db.Model):
    __tablename__ = 'biosample_attributes'
    id = db.Column(db.Integer, server_default=text("nextval('biosample_attributes_id_seq')"), primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey('ncbi_metadata.id'), nullable=False, index=True)
    k = db.Column(db.String, nullable=False, index=True)
    v = db.Column(db.String, nullable=False)
    
    def to_dict(self):
        return dict(id=self.id,
                    run_id=self.run_id,
                    k=self.k,
                    v=self.v)

class ParsedSampleAttribute(db.Model):
    __tablename__ = 'parsed_sample_attributes'
    id = db.Column(db.Integer, server_default=text("nextval('parsed_sample_attributes_id_seq')"), primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey('ncbi_metadata.id'), nullable=False, index=True)
    collection_year = db.Column(db.Integer)
    collection_month = db.Column(db.Integer)
    latitude = db.Column(db.Float, index=True)
    longitude = db.Column(db.Float, index=True)
    depth = db.Column(db.Float)
    temperature = db.Column(db.Float)
    host_or_not_prediction = db.Column(db.String)
    host_or_not_recorded = db.Column(db.String)
    host_or_not_mature = db.Column(db.String)
    # sample  bacterial_archaeal_bases        metagenome_size read_fraction   warning
    bacterial_archaeal_bases = db.Column(db.Float)
    # metagenome_size = db.Column(db.Float) #=> use mbases from ncbi_metadata
    smf = db.Column(db.Float)
    smf_warning = db.Column(db.Boolean)
    known_species_fraction = db.Column(db.Float)
    globdb_known_species_fraction = db.Column(db.Float)
    low_complexity = db.Column(db.Boolean)
    top1_order_fraction = db.Column(db.Float)
    top3_order_fraction = db.Column(db.Float)
    # Backend classification flags (populated in generate_backend_db). Strict T/F,
    # never NULL except the domain_only_* pair which is NULL when no profile was
    # loaded for that sample under the given taxonomy.
    non_metagenome_organism_strict = db.Column(db.Boolean)
    non_metagenome_organism_loose = db.Column(db.Boolean)
    synthetic = db.Column(db.Boolean)
    rna_or_non_dna_strict = db.Column(db.Boolean)
    rna_or_non_dna_loose = db.Column(db.Boolean)
    domain_only_gtdb = db.Column(db.Boolean)
    domain_only_globdb = db.Column(db.Boolean)
    domain_only_both = db.Column(db.Boolean)
    # --- BEGIN metalog meta_ columns (generated; see metaup_sandpiper) ---
    # Auto-generated from the metaup_sandpiper slim file header. All metalog
    # extended-metadata fields, stored as String (source data is heterogeneous,
    # e.g. '0-0.1', 'unknown'). Populated by the parsed_metadata stage when
    # METALOG_EXTENSION_METADATA is configured; NULL otherwise. Regenerate with
    # scripts/gen_meta_columns.py if the metalog schema changes.
    meta_blood_group = db.Column(db.String)
    meta_description = db.Column(db.String)
    meta_dol_range = db.Column(db.String)
    meta_drug_antibiotic_last3y = db.Column(db.String)
    meta_field_nominal_c = db.Column(db.String)
    meta_other_meds = db.Column(db.String)
    meta_acetate_um = db.Column(db.String)
    meta_added_matter = db.Column(db.String)
    meta_age_category = db.Column(db.String)
    meta_age_days = db.Column(db.String)
    meta_age_months = db.Column(db.String)
    meta_age_range = db.Column(db.String)
    meta_age_years = db.Column(db.String)
    meta_alkalinity = db.Column(db.String)
    meta_ammonium_mg_l = db.Column(db.String)
    meta_ammonium_um = db.Column(db.String)
    meta_amy1cn = db.Column(db.String)
    meta_antibiotic = db.Column(db.String)
    meta_antibiotic_dosage = db.Column(db.String)
    meta_artificial = db.Column(db.String)
    meta_available_info = db.Column(db.String)
    meta_birth_country = db.Column(db.String)
    meta_birth_gestational_age_weeks = db.Column(db.String)
    meta_birth_mode = db.Column(db.String)
    meta_birth_term_status = db.Column(db.String)
    meta_birth_weight_kg = db.Column(db.String)
    meta_bmi = db.Column(db.String)
    meta_bmi_range = db.Column(db.String)
    meta_bristol_stool_scale = db.Column(db.String)
    meta_butyrate_um = db.Column(db.String)
    meta_calcium_mg_l = db.Column(db.String)
    meta_captivity_status = db.Column(db.String)
    meta_captivity_status_full = db.Column(db.String)
    meta_carbon_dioxide_um = db.Column(db.String)
    meta_cause_of_death = db.Column(db.String)
    meta_chloride_mg_l = db.Column(db.String)
    meta_climatic_zone = db.Column(db.String)
    meta_cohort = db.Column(db.String)
    meta_collection_date = db.Column(db.String)
    meta_collection_date_end = db.Column(db.String)
    meta_common_timepoint = db.Column(db.String)
    meta_comorbidities = db.Column(db.String)
    meta_couple_id = db.Column(db.String)
    meta_couple_timepoint = db.Column(db.String)
    meta_cultivation_condition = db.Column(db.String)
    meta_cultivation_duration = db.Column(db.String)
    meta_days_since_antibiotics = db.Column(db.String)
    meta_days_since_fmt = db.Column(db.String)
    meta_depth_meters = db.Column(db.String)
    meta_diet = db.Column(db.String)
    meta_diet_full = db.Column(db.String)
    meta_dissolved_organic_carbon_um = db.Column(db.String)
    meta_dissolved_oxygen_um = db.Column(db.String)
    meta_doi = db.Column(db.String)
    meta_donor_d0 = db.Column(db.String)
    meta_donor_d28 = db.Column(db.String)
    meta_elevation_meters = db.Column(db.String)
    meta_enriched_soil = db.Column(db.String)
    meta_environment_biome = db.Column(db.String)
    meta_environment_feature = db.Column(db.String)
    meta_environment_material = db.Column(db.String)
    meta_environmental_package = db.Column(db.String)
    meta_ethnicity = db.Column(db.String)
    meta_family = db.Column(db.String)
    meta_ferric_iron_um = db.Column(db.String)
    meta_ferrous_iron_um = db.Column(db.String)
    meta_ferrous_um = db.Column(db.String)
    meta_filtration_lower_threshold = db.Column(db.String)
    meta_filtration_lower_threshold_kda = db.Column(db.String)
    meta_filtration_lower_threshold_um = db.Column(db.String)
    meta_filtration_upper_threshold_um = db.Column(db.String)
    meta_fmt_donor = db.Column(db.String)
    meta_food_name = db.Column(db.String)
    meta_formate_um = db.Column(db.String)
    meta_full_description = db.Column(db.String)
    meta_geographic_location = db.Column(db.String)
    meta_gestational_age_weeks = db.Column(db.String)
    meta_gestational_state = db.Column(db.String)
    meta_group = db.Column(db.String)
    meta_height_cm = db.Column(db.String)
    meta_hip_cm = db.Column(db.String)
    meta_host = db.Column(db.String)
    meta_host_common_name = db.Column(db.String)
    meta_host_scientific_name = db.Column(db.String)
    meta_host_tax_id = db.Column(db.String)
    meta_host_tax_scientific_name = db.Column(db.String)
    meta_housing_lab = db.Column(db.String)
    meta_hydrosulfide_um = db.Column(db.String)
    meta_infant_id = db.Column(db.String)
    meta_intervention = db.Column(db.String)
    meta_intervention_full = db.Column(db.String)
    meta_iron_mg_l = db.Column(db.String)
    meta_iron_um = db.Column(db.String)
    meta_isolation_source = db.Column(db.String)
    meta_land_use_category = db.Column(db.String)
    meta_land_use_full = db.Column(db.String)
    meta_last_change = db.Column(db.String)
    meta_latitude = db.Column(db.String)
    meta_lifestyle = db.Column(db.String)
    meta_linked_to = db.Column(db.String)
    meta_location = db.Column(db.String)
    meta_location_name = db.Column(db.String)
    meta_location_resolution = db.Column(db.String)
    meta_longitude = db.Column(db.String)
    meta_magnesium_mg_l = db.Column(db.String)
    meta_manganese_um = db.Column(db.String)
    meta_mean_annual_precipitation_mm = db.Column(db.String)
    meta_mean_annual_temperature = db.Column(db.String)
    meta_medical_history_notduringstudy = db.Column(db.String)
    meta_medical_operation = db.Column(db.String)
    meta_medication = db.Column(db.String)
    meta_medication_full = db.Column(db.String)
    meta_medication_with_parents = db.Column(db.String)
    meta_medicinal_plant = db.Column(db.String)
    meta_menopausal_status = db.Column(db.String)
    meta_methane_um = db.Column(db.String)
    meta_nitrate_mg_l = db.Column(db.String)
    meta_nitrate_nitrite_um = db.Column(db.String)
    meta_nitrate_um = db.Column(db.String)
    meta_nitrite_mg_l = db.Column(db.String)
    meta_nitrite_um = db.Column(db.String)
    meta_nitrogen_dioxide_um = db.Column(db.String)
    meta_nitrogen_percent = db.Column(db.String)
    meta_note = db.Column(db.String)
    meta_original_sample_name = db.Column(db.String)
    meta_original_timepoint = db.Column(db.String)
    meta_oxygen_um = db.Column(db.String)
    meta_ph = db.Column(db.String)
    meta_ph_range = db.Column(db.String)
    meta_phenotypic_information = db.Column(db.String)
    meta_phosphate_um = db.Column(db.String)
    meta_phosphorus_mg_l = db.Column(db.String)
    meta_phosphorus_um = db.Column(db.String)
    meta_plant = db.Column(db.String)
    meta_pmid = db.Column(db.String)
    meta_pooled_individuals = db.Column(db.String)
    meta_potassium_mg_l = db.Column(db.String)
    meta_pregnancy_week = db.Column(db.String)
    meta_pregnant = db.Column(db.String)
    meta_probiotic = db.Column(db.String)
    meta_propionate_um = db.Column(db.String)
    meta_protocol_label = db.Column(db.String)
    meta_provider = db.Column(db.String)
    meta_range_days_since_abxs = db.Column(db.String)
    meta_range_days_since_antibiotics = db.Column(db.String)
    meta_range_days_since_medication = db.Column(db.String)
    meta_recipient_donor = db.Column(db.String)
    meta_salinity = db.Column(db.String)
    meta_salinity_ppm = db.Column(db.String)
    meta_salinity_ppt = db.Column(db.String)
    meta_sample_alias = db.Column(db.String)
    meta_sample_collection_timepoint = db.Column(db.String)
    meta_sample_description = db.Column(db.String)
    meta_sample_title = db.Column(db.String)
    meta_sampling_campaign = db.Column(db.String)
    meta_sampling_platform = db.Column(db.String)
    meta_sampling_site = db.Column(db.String)
    meta_sampling_station = db.Column(db.String)
    meta_sex = db.Column(db.String)
    meta_silicate_um = db.Column(db.String)
    meta_site_description = db.Column(db.String)
    meta_skin_site_type = db.Column(db.String)
    meta_smoker = db.Column(db.String)
    meta_sodium_mg_l = db.Column(db.String)
    meta_specific_material = db.Column(db.String)
    meta_stool_consistency = db.Column(db.String)
    meta_strain = db.Column(db.String)
    meta_study_accession = db.Column(db.String)
    meta_study_code = db.Column(db.String)
    meta_subject_disease_status = db.Column(db.String)
    meta_subject_disease_status_full = db.Column(db.String)
    meta_subject_id = db.Column(db.String)
    meta_sulfate_mg_l = db.Column(db.String)
    meta_sulfate_um = db.Column(db.String)
    meta_sulfide_um = db.Column(db.String)
    meta_synbiotic = db.Column(db.String)
    meta_tax_id = db.Column(db.String)
    meta_temperature = db.Column(db.String)
    meta_temperature_range = db.Column(db.String)
    meta_time_period = db.Column(db.String)
    meta_timepoint = db.Column(db.String)
    meta_timepoint_note = db.Column(db.String)
    meta_timeseries_available = db.Column(db.String)
    meta_timeseries_count = db.Column(db.String)
    meta_timeseries_duration = db.Column(db.String)
    meta_tissue_type = db.Column(db.String)
    meta_total_dissolved_nitrogen_um = db.Column(db.String)
    meta_total_iron_um = db.Column(db.String)
    meta_total_manganese_um = db.Column(db.String)
    meta_total_nitrate = db.Column(db.String)
    meta_total_organic_carbon = db.Column(db.String)
    meta_type_of_birth = db.Column(db.String)
    meta_vaccine_name = db.Column(db.String)
    meta_vaginal_ph = db.Column(db.String)
    meta_vegetation = db.Column(db.String)
    meta_vegetation_full = db.Column(db.String)
    meta_village = db.Column(db.String)
    meta_waist_cm = db.Column(db.String)
    meta_water_depth_meters = db.Column(db.String)
    meta_weight_kg = db.Column(db.String)
    # --- END metalog meta_ columns ---
    # Backend-only classification flags (not surfaced on the website; intentionally
    # excluded from to_displayable_dict). Populated in the 'tags' stage by
    # add_metagenome_classification_flags() in bin/generate_backend_db.
    non_metagenome_organism_strict = db.Column(db.Boolean)
    non_metagenome_organism_loose = db.Column(db.Boolean)
    synthetic = db.Column(db.Boolean)
    rna_or_non_dna_strict = db.Column(db.Boolean)
    rna_or_non_dna_loose = db.Column(db.Boolean)
    # Per-taxonomy "nothing assigned below domain-level" flags (backend-only,
    # excluded from to_displayable_dict). Profile-derived, so they differ by
    # taxonomy_type. domain_only_gtdb / domain_only_globdb are set during the
    # stage2 condensed loads in fill_condensed_and_taxonomy_tables(); NULL means
    # no profile was loaded for that sample under that taxonomy. domain_only_both
    # = domain_only_gtdb AND domain_only_globdb, derived in the 'tags' stage.
    domain_only_gtdb = db.Column(db.Boolean)
    domain_only_globdb = db.Column(db.Boolean)
    domain_only_both = db.Column(db.Boolean)
    def to_displayable_dict(self):
        return dict(
            collection_year=self.collection_year,
            collection_month=self.collection_month,
            latitude=self.latitude,
            longitude=self.longitude,
            depth=self.depth,
            temperature=self.temperature,
            host_or_not_prediction=self.host_or_not_prediction,
            host_or_not_recorded=self.host_or_not_recorded,
            host_or_not_mature=self.host_or_not_mature,
            bacterial_archaeal_bases=self.bacterial_archaeal_bases,
            smf=self.smf,
            smf_warning=self.smf_warning,
            known_species_fraction=self.known_species_fraction,
            globdb_known_species_fraction=self.globdb_known_species_fraction,
            low_complexity=self.low_complexity,
            top1_order_fraction=self.top1_order_fraction,
            non_metagenome_organism_strict=self.non_metagenome_organism_strict,
            non_metagenome_organism_loose=self.non_metagenome_organism_loose,
            synthetic=self.synthetic,
            rna_or_non_dna_strict=self.rna_or_non_dna_strict,
            rna_or_non_dna_loose=self.rna_or_non_dna_loose,
            domain_only_gtdb=self.domain_only_gtdb,
            domain_only_globdb=self.domain_only_globdb,
            domain_only_both=self.domain_only_both)

    def metalog_rows(self):
        """Populated metalog meta_ fields, as RunMetadataTable rows.

        200 meta_ columns are defined but only a handful hold a value for any
        given run, so this is built from what is actually present rather than
        from the schema -- returning all of them would be mostly nulls and a
        large payload. Empty list when the run has no metalog match, which the
        front end uses to decide whether to show the section at all.
        """
        descriptions = {
            'age_category': 'an automatically generated age category derived from age years and age range. Categories include baby, child, adolescent and adult; combined categories may be used when an age range spans more than one category.',
            'age_days': 'the subject or animal\'s age in days at the time the sample was collected.',
            'age_months': 'the subject or animal\'s age in months at the time the sample was collected.',
            'age_range': 'the subject or animal\'s approximate age range when an exact age is unavailable.',
            'age_years': 'the subject or animal\'s age in years. Decimal values may be used for ages younger than one year.',
            'artificial': 'whether the sample was technically modified, experimentally manipulated or substantially affected by the passage of time. An empty value indicates a natural, non-modified sample.',
            'added_matter': 'matter intentionally added to the sample or experimental system, such as nutrients, oil, dispersant, manure or antibiotics.',
            'antibiotic': 'the antibiotic administered to or taken by the subject or animal.',
            'antibiotic_dosage': 'the reported dosage of the antibiotic administered to or taken by the subject or animal.',
            'alkalinity': 'the alkalinity measured in the sample or at the sampling location.',
            'amy1cn': 'the subject\'s AMY1 gene copy number.',
            'birth_country': 'the country in which the subject was born.',
            'birth_gestational_age_weeks': 'the gestational age at birth, measured in weeks.',
            'birth_mode': 'the mode by which the subject was born, such as vaginal or caesarean delivery.',
            'birth_term_status': 'whether the subject was born preterm, at term or post-term.',
            'birth_weight_kg': 'the subject\'s weight at birth, measured in kilograms.',
            'blood_group': 'the subject\'s reported blood group.',
            'birth_year': 'the year in which the subject was born.',
            'bmi': 'the subject\'s body mass index, measured in kilograms per square metre, at the time the sample was collected.',
            'bmi_range': 'the approximate range of the subject\'s body mass index when an exact value is unavailable.',
            'bristol_stool_scale': 'the stool type recorded using the Bristol Stool Form Scale.',
            'captivity_status': 'whether the sampled animal was captive or free-living.',
            'captivity_status_full': 'a more detailed description of the sampled animal\'s captivity status.',
            'cause_of_death': 'the reported cause of the subject or animal\'s death.',
            'climatic_zone': 'the broad climatic zone of the sampling location.',
            'collection_date': 'the date on which the sample was collected.',
            'collection_date_end': 'the end date of the sample collection period when collection spans a date range.',
            'cohort': 'the study cohort to which the subject or sample belongs, such as an exercise, sedentary or validation cohort.',
            'common_timepoint': 'a harmonised label for the sampling time point, such as day zero or a specified number of months.',
            'couple_id': 'the study-specific identifier assigned to a couple.',
            'couple_timepoint': 'the study-provided sampling time point associated with a couple.',
            'comorbidities': 'additional diseases or medical conditions reported for the subject.',
            'cultivation_condition': 'the conditions under which the sample or organisms were cultivated.',
            'cultivation_duration': 'the length of time for which the sample or organisms were cultivated.',
            'days_since_antibiotics': 'the number of days between the subject\'s antibiotic exposure and sample collection.',
            'days_since_fmt': 'the number of days between faecal microbiota transplantation and sample collection.',
            'description': 'a description of the sample recorded in Metalog or retained from the original study metadata.',
            'dol_range': 'the reported range for Metalog\'s DOL variable. The meaning and unit of DOL are retained from the source study.',
            'drug_antibiotic_last3y': 'whether antibiotic drug use was reported during the three years preceding sample collection.',
            'depth_meters': 'the vertical distance in metres below the relevant surface at which the sample was collected. For soil or sediment, depth is measured below the soil or sediment surface.',
            'diet': 'information about the subject or animal\'s diet at the time of sample collection. Metalog standardises diets into broad categories.',
            'diet_full': 'a more detailed description of the subject or animal\'s diet than the standardised diet category.',
            'doi': 'the Digital Object Identifier of an associated publication.',
            'donor_d0': 'the identifier of the donor associated with the subject or sample at day zero.',
            'donor_d28': 'the identifier of the donor associated with the subject or sample at day 28.',
            'elevation_meters': 'the elevation of the sampling location in metres relative to mean sea level. Negative values indicate locations below mean sea level.',
            'environment_feature': 'an ENVO ontology term, or a UBERON term when appropriate, describing the environmental setting from which the sample originated.',
            'environment_material': 'an ENVO ontology term, or a UBERON term when appropriate, describing the physical material collected.',
            'environment_biome': 'an ENVO ontology term describing the broad biome associated with the sample.',
            'environmental_package': 'the environmental metadata package or sample-category standard associated with the sample.',
            'enriched_soil': 'whether the soil sample was experimentally enriched.',
            'ethnicity': 'the subject\'s ethnicity as reported in the associated publication or study metadata.',
            'filtration_lower_threshold_um': 'the lower size threshold used during filtration, measured in micrometres. This generally represents the pore size of the collection filter, with retained material kept for sequencing.',
            'filtration_upper_threshold_um': 'the upper size threshold used during filtration, measured in micrometres. This generally represents the pore size of a pre-filter, with retained material excluded from sequencing for that fraction.',
            'filtration_lower_threshold_kda': 'the lower molecular-mass threshold used during filtration, reported in kilodaltons.',
            'filtration_lower_threshold': 'the lower threshold used during filtration. Its unit and exact filtration basis are retained from the source study where provided.',
            'fmt_donor': 'the identifier or description of the faecal microbiota transplantation donor associated with the sample.',
            'food_name': 'the name of the food associated with the sample.',
            'full_description': 'a detailed description of the sample retained from the original study metadata.',
            'geographic_location': 'the country, territory, ocean or other broad geographic region from which the sample originated.',
            'gestational_age_weeks': 'the gestational age in weeks at the time the sample was collected.',
            'gestational_state': 'the subject\'s pregnancy or gestational state at the time the sample was collected.',
            'height_cm': 'the subject\'s body height in centimetres at the time the sample was collected.',
            'hip_cm': 'the subject\'s hip circumference in centimetres at the time the sample was collected.',
            'host': 'the host organism associated with the sample.',
            'host_common_name': 'the common name of the host organism associated with the sample.',
            'host_scientific_name': 'the scientific name of the host organism associated with the sample.',
            'host_tax_id': 'the NCBI Taxonomy identifier of the host organism associated with the sample.',
            'host_tax_scientific_name': 'the scientific name associated with the recorded host taxonomy identifier.',
            'housing_lab': 'information about laboratory housing conditions for the sampled animal.',
            'infant_id': 'the study-specific identifier assigned to the infant subject.',
            'intervention': 'a broad categorisation of an intervention received by the subject or animal, such as antibiotics, dietary intervention, drug treatment, probiotics or vaccination.',
            'intervention_full': 'a more detailed description of the intervention than the standardised intervention category.',
            'isolation_source': 'the source material or environment from which the sample or organism was isolated.',
            'land_use_category': 'a standardised category describing how land at the sampling location was used.',
            'land_use_full': 'a more detailed description of land use at the sampling location.',
            'last_change': 'the date or time of the most recent change to the Metalog record.',
            'linked_to': 'the identifier of a related subject or sample, such as the mother linked to an infant subject.',
            'latitude': 'the latitude of the sample\'s geographic origin, reported in decimal degrees.',
            'location': 'a more detailed description of the sampling location than the broad country or region recorded in geographic location.',
            'location_resolution': 'the precision of the geographic location, such as exact location, site, city, region, country or continent.',
            'location_name': 'the name assigned to the sampling location.',
            'lifestyle': 'the subject\'s lifestyle category as reported in the associated study.',
            'longitude': 'the longitude of the sample\'s geographic origin, reported in decimal degrees.',
            'mean_annual_precipitation_mm': 'the mean annual precipitation at the sampling location, reported in millimetres.',
            'mean_annual_temperature': 'the mean annual temperature at the sampling location, reported in degrees Celsius.',
            'medication': 'information about medication taken by or administered to the subject or animal. Drug names, drug classes or Anatomical Therapeutic Chemical codes may be recorded.',
            'medication_full': 'a more detailed description of medication than the standardised medication field.',
            'medication_with_parents': 'medication represented with its mapped parent drug classes or categories.',
            'medical_history_notduringstudy': 'medical conditions in the subject\'s history that were not recorded as occurring during the study.',
            'medicinal_plant': 'a medicinal plant associated with the sample or intervention.',
            'medical_operation': 'a medical or surgical procedure received by the subject.',
            'menopausal_status': 'the subject\'s menopausal status at the time the sample was collected.',
            'note': 'additional notes captured for the sample in Metalog.',
            'other_meds': 'other medications taken by the subject that are not represented in the primary medication field.',
            'original_sample_name': 'the sample name used in the original study metadata before Metalog harmonisation.',
            'original_timepoint': 'the sampling time-point value or label retained from the original study metadata before Metalog harmonisation.',
            'ph': 'the pH of the soil, water or other environmental material at the sampling site. An exact numerical value is preferred.',
            'ph_range': 'the reported pH range when an exact pH value is unavailable.',
            'phenotypic_information': 'information about the phenotype of the sample or host, such as whether a dog was lean to normal or overweight to obese.',
            'plant': 'the plant species or plant material associated with the sample.',
            'pmid': 'the PubMed identifier of an associated publication.',
            'pooled_individuals': 'the number of individuals whose material was combined in the sample, or an indication that the sample was pooled.',
            'pregnancy_week': 'the week of pregnancy at the time the sample was collected.',
            'pregnant': 'whether the subject was pregnant at the time the sample was collected.',
            'probiotic': 'the probiotic administered to or consumed by the subject or animal.',
            'protocol_label': 'the label identifying the original-publication protocol used to produce the sample, such as its filtration and preservation protocol. It is recorded only when supplied by the original publication.',
            'provider': 'the person, organisation or facility that provided the sample or associated metadata.',
            'range_days_since_abxs': 'the approximate range, in days, between antibiotic exposure and sample collection.',
            'range_days_since_antibiotics': 'the approximate range, in days, between antibiotic exposure and sample collection.',
            'range_days_since_medication': 'the approximate range, in days, between medication exposure and sample collection.',
            'recipient_donor': 'whether the sample came from a treatment recipient or a donor.',
            'salinity': 'the salinity of the water at the time of sample collection, reported in practical salinity units.',
            'salinity_ppm': 'the salinity of the sample, reported in parts per million.',
            'salinity_ppt': 'the salinity of the sample, reported in parts per thousand.',
            'sample_alias': 'a unique sample identifier used to associate the sample with its study and experiment.',
            'sampling_campaign': 'the finite or ongoing activity under which samples were collected, such as a research cruise, time-series programme, expedition or mesocosm experiment.',
            'sampling_platform': 'the vessel, structure or other platform from which the sampling equipment was deployed.',
            'sampling_station': 'the named or numbered station at which the sample or associated environmental measurements were collected.',
            'sample_collection_timepoint': 'the study-defined sampling time point at which the sample was collected.',
            'sample_description': 'a description of the sample provided by Metalog or the associated study.',
            'sample_title': 'the title or short name assigned to the sample.',
            'sampling_site': 'the named or described site at which the sample was collected.',
            'site_description': 'a description of the site at which the sample was collected.',
            'specific_material': 'a more specific description of the environmental material collected, such as hospital wastewater, wastewater influent or effluent, or river sediment.',
            'sex': 'the subject or animal\'s sex as reported in the associated publication or study metadata.',
            'skin_site_type': 'the anatomical skin-site category from which the sample was collected.',
            'smoker': 'whether the subject was reported to smoke at the time of the study.',
            'stool_consistency': 'the reported consistency of the stool sample.',
            'group': 'the number or identifier of the study-defined group to which the subject or sample belongs.',
            'family': 'the study-specific identifier of the family to which the subject belongs.',
            'strain': 'the microbial, animal or plant strain associated with the sample.',
            'study_accession': 'the public database accession assigned to the study.',
            'study_code': 'the code or short identifier used for the study in Metalog.',
            'subject_disease_status': 'the subject or animal\'s health or disease status. This describes disease status rather than response to treatment.',
            'subject_disease_status_full': 'a more detailed description of the subject or animal\'s health or disease status.',
            'subject_id': 'the study-specific identifier assigned to the sampled subject or animal.',
            'synbiotic': 'the synbiotic administered to or consumed by the subject or animal.',
            'tax_id': 'the NCBI Taxonomy identifier associated with the sample.',
            'temperature': 'the temperature in degrees Celsius at the time the sample was collected.',
            'temperature_range': 'the reported temperature range in degrees Celsius when an exact temperature is unavailable.',
            'time_period': 'the historical or archaeological period associated with the sample, expressed as a calendar range or as years before present where applicable.',
            'timepoint_note': 'an explanatory note about the sampling time point, such as the visit window, date precision, or subject age or sample stage.',
            'timepoint': 'the number of days between collection of this sample and collection of the first sample from the same subject or animal. A longitudinal series begins at day zero.',
            'timeseries_available': 'an automatically generated field indicating whether more than one sampling time point is available for the subject.',
            'timeseries_count': 'the number of samples or sampling time points available in the subject\'s longitudinal series.',
            'timeseries_duration': 'the total duration of the subject\'s longitudinal sampling series, generally expressed in days.',
            'tissue_type': 'the tissue type from which the sample was collected.',
            'total_nitrate': 'the total nitrate measured in the sample; the unit is retained in the Metalog value where provided.',
            'total_organic_carbon': 'the total organic carbon measured in the sample; the unit is retained in the Metalog value where provided.',
            'type_of_birth': 'the mode by which the subject was born, such as vaginal or caesarean delivery.',
            'vaccine_name': 'the name of the vaccine administered to the subject or animal.',
            'vaginal_ph': 'the vaginal pH measured at or around the time of sample collection.',
            'vegetation': 'a standardised description of vegetation at the sampling location.',
            'vegetation_full': 'a more detailed description of vegetation at the sampling location.',
            'village': 'the village associated with the sampling location.',
            'waist_cm': 'the subject\'s waist circumference in centimetres at the time the sample was collected.',
            'water_depth_meters': 'the total water-column depth in metres at the sampling location.',
            'weight_kg': 'the subject or animal\'s body weight in kilograms at the time the sample was collected.',
        }
        rows = []
        for column in self.__table__.columns:
            if not column.name.startswith('meta_'):
                continue
            value = getattr(self, column.name)
            if value is None or str(value).strip() == '':
                continue
            field_name = column.name[len('meta_'):]
            description = descriptions.get(field_name)
            if description is None and field_name.endswith('_um'):
                measurement = field_name[:-3].replace('_', ' ')
                description = ('the {0} concentration in the sample, reported '
                               'in micromolar units.'.format(measurement))
            elif description is None and field_name.endswith('_mg_l'):
                measurement = field_name[:-5].replace('_', ' ')
                description = ('the {0} concentration in the sample, reported '
                               'in milligrams per litre.'.format(measurement))
            elif description is None and field_name.endswith('_percent'):
                measurement = field_name[:-8].replace('_', ' ')
                description = 'the {0} content of the sample, reported as a percentage.'.format(measurement)
            rows.append(dict(
                k=field_name.replace('_', ' ').capitalize(),
                v=value,
                description=description or
                            'an additional metadata field recorded in Metalog for this run.',
                is_custom=False))
        return sorted(rows, key=lambda row: row['k'])


class StudyLink(db.Model):
    __tablename__ = 'study_links'
    id = db.Column(db.Integer, server_default=text("nextval('study_links_id_seq')"), primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey('ncbi_metadata.id'), nullable=False, index=True)
    study_id = db.Column(db.String)
    database = db.Column(db.String)
    label = db.Column(db.String)
    url = db.Column(db.String)

    def to_displayable_dict(self):
        if self.database:
            return dict(
                study_id=self.study_id,
                database=self.database)
        else:
            return dict(
                label=self.label,
                url=self.url)


class NcbiMetadata(db.Model):
    __tablename__ = 'ncbi_metadata'
    id = db.Column(db.Integer, server_default=text("nextval('ncbi_metadata_id_seq')"), primary_key=True)
    # acc,
    # assay_type,
    # center_name,
    # experiment,
    # sample_name,
    # instrument,
    # libraryselection,
    # librarysource,
    # platform,
    # sample_acc,
    # biosample,
    # organism,
    # sra_study,
    # releasedate,
    # bioproject,
    # avgspotlen,
    # mbases,
    # insertsize,
    # library_name,
    # biosamplemodel_sam,
    # collection_date_sam,
    # geo_loc_name_country_calc,
    # geo_loc_name_country_continent_calc,
    # geo_loc_name_sam,
    # sample_name_sam,
    # attributes
    acc = db.Column(db.String, nullable=False, index=True)
    assay_type = db.Column(db.String)
    center_name = db.Column(db.String)
    experiment = db.Column(db.String, index=True)
    sample_name = db.Column(db.String)
    model = db.Column(db.String)
    librarylayout = db.Column(db.String)
    libraryselection = db.Column(db.String)
    librarysource = db.Column(db.String)
    platform = db.Column(db.String)
    sample_acc = db.Column(db.String, index=True)
    biosample = db.Column(db.String, index=True)
    taxon_name = db.Column(db.String)
    sra_study = db.Column(db.String, index=True)
    published = db.Column(db.DateTime)
    bioproject = db.Column(db.String, index=True)
    # mbytes = db.Column(db.Integer)
    # avgspotlen = db.Column(db.Integer)
    bases = db.Column(db.BigInteger)
    spots = db.Column(db.BigInteger)
    insertsize = db.Column(db.Integer)
    library_name = db.Column(db.String)
    collection_date_parsed = db.Column(db.DateTime)
    geo_loc_name_country_calc = db.Column(db.String)
    geo_loc_name_country_continent_calc = db.Column(db.String)
    geo_loc_name = db.Column(db.String)
    ena_first_public_run = db.Column(db.String)
    ena_last_update_run = db.Column(db.String)

    # Below are fields found from kingfisher annotate
    experiment_title = db.Column(db.String)
    library_strategy = db.Column(db.String)
    organisation_name = db.Column(db.String)
    organisation_department = db.Column(db.String)
    organisation_institution = db.Column(db.String)
    organisation_street = db.Column(db.String)
    organisation_city = db.Column(db.String)
    organisation_country = db.Column(db.String)
    organisation_contact_name = db.Column(db.String)
    study_title = db.Column(db.String, index=True) # Index because /project matches via title when abstract is not available
    study_abstract = db.Column(db.String, index=True) # Index for /project
    design_description = db.Column(db.String)
    read1_length_average = db.Column(db.Float)
    read1_length_stdev = db.Column(db.Float)
    read2_length_average = db.Column(db.Float)
    read2_length_stdev = db.Column(db.Float)

    study_links = db.relationship('StudyLink', backref='ncbi_metadata', foreign_keys=[StudyLink.run_id])
    biosample_attributes = db.relationship('BiosampleAttribute', backref='ncbi_metadata', foreign_keys=[BiosampleAttribute.run_id])
    condensed_profiles = db.relationship('CondensedProfile', back_populates='ncbi_metadata', foreign_keys=[CondensedProfile.run_id])
    parsed_sample_attributes = db.relationship('ParsedSampleAttribute', backref='ncbi_metadata', foreign_keys=[ParsedSampleAttribute.run_id])

    def to_displayable_dict(self):
        biosample_attrs = [x for x in self.biosample_attributes if x.k != 'primary_search']
        # Temporary fix - somehow study_links are in the wrong table atm. HACK!!
        study_links_tmp = [x.v for  x in biosample_attrs if x.k == 'study_links']
        print('tmp: '+str(study_links_tmp)+' type is '+str(type(study_links_tmp)))
        # study_links_tmp currently a list of str e.g. ([{"db": "pubmed", "id": "29669589"}])
        # convert to list of dicts
        study_links = [study_link.to_displayable_dict() for study_link in self.study_links]
        for sl0 in study_links_tmp:
            try:
                print("Evaluating study_links sl0: "+str(sl0))
                sl = eval(sl0)
                for s in sl:
                    if 'id' in s:
                        s['study_id'] = s['id']
                        del s['id']
                    if 'db' in s:
                        s['database'] = s['db']
                        del s['db']
                    if 'label' in s:
                        s['label'] = s['label']
                    if 'url' in s:
                        s['url'] = s['url']
                    study_links.append(s)
            except Exception as e:
                print(f"Error parsing study_links: {e}")
        return dict(acc=self.acc,
                    assay_type=self.assay_type,
                    center_name=self.center_name,
                    experiment=self.experiment,
                    sample_name=self.sample_name,
                    model=self.model,
                    librarylayout=self.librarylayout,
                    libraryselection=self.libraryselection,
                    librarysource=self.librarysource,
                    platform=self.platform,
                    sample_acc=self.sample_acc,
                    biosample=self.biosample,
                    taxon_name=self.taxon_name,
                    sra_study=self.sra_study,
                    releasedate=self.published.strftime('%-d %B %Y') if self.published else None,
                    bioproject=self.bioproject,
                    # bytes=self.bytes,
                    # loaddate=self.loaddate,
                    # avgspotlen=self.avgspotlen,
                    bases=self.bases,
                    spots=self.spots,
                    insertsize=self.insertsize,
                    library_name=self.library_name,
                    collection_date_parsed=self.collection_date_parsed.strftime('%-d %B %Y') if self.collection_date_parsed else None,
                    geo_loc_name_country_calc=self.geo_loc_name_country_calc,
                    geo_loc_name_country_continent_calc=self.geo_loc_name_country_continent_calc,
                    geo_loc_name=self.geo_loc_name,
                    ena_first_public_run=self.ena_first_public_run,
                    ena_last_update_run=self.ena_last_update_run,
                    experiment_title=self.experiment_title,
                    library_strategy=self.library_strategy,
                    organisation_department=self.organisation_department,
                    organisation_institution=self.organisation_institution,
                    organisation_street=self.organisation_street,
                    organisation_city=self.organisation_city,
                    organisation_country=self.organisation_country,
                    organisation_contact_name=self.organisation_contact_name,
                    study_title=self.study_title,
                    study_abstract=self.study_abstract,
                    design_description=self.design_description,
                    read1_length_average=self.read1_length_average,
                    read1_length_stdev=self.read1_length_stdev,
                    read2_length_average=self.read2_length_average,
                    read2_length_stdev=self.read2_length_stdev,
                    study_links=study_links,
                    biosample_attributes=[{'k': x.k, 'v': x.v} for x in self.biosample_attributes if x.k != 'primary_search'],
                    parsed_sample_attributes=self.parsed_sample_attributes[0].to_displayable_dict(),
                    metalog_metadata=self.parsed_sample_attributes[0].metalog_rows())

class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, server_default=text("nextval('tags_id_seq')"), primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)
    description = db.Column(db.String, nullable=False)

    def to_displayable_dict(self):
        return dict(
            name=self.name,
            description=self.description)

class RunTag(db.Model):
    __tablename__ = 'run_tags'
    id = db.Column(db.Integer, server_default=text("nextval('run_tags_id_seq')"), primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey('ncbi_metadata.id'), nullable=False)
    tag_id = db.Column(db.Integer, db.ForeignKey('tags.id'), nullable=False)

    def to_displayable_dict(self):
        return dict(
            run_id=self.run_id,
            tag_id=self.tag_id)


class IndicatorHabitatScore(db.Model):
    '''Per-sample, per-habitat indicator-genus abundance score from IndicPiper
    (indicspecies::multipatt IndVal analysis run against Sandpiper's own current
    data -- see indicpiper_custom/). One row per (run_id, habitat) with a nonzero
    score: the summed relative_abundance of every genus flagged as an indicator
    of that habitat, for that sample. Sparse by design -- ~15.6% of the dense
    (sample x habitat) matrix is nonzero (verified 2026-08 against the live DB),
    so a row-per-nonzero-pair table is used instead of one column per habitat on
    parsed_sample_attributes, matching the Tag/RunTag pattern rather than the
    add_metagenome_classification_flags wide-column pattern. Backend-only for
    now -- not surfaced via to_displayable_dict / the API response.
    '''
    __tablename__ = 'indicator_habitat_scores'
    id = db.Column(db.Integer, server_default=text("nextval('indicator_habitat_scores_id_seq')"), primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey('ncbi_metadata.id'), nullable=False, index=True)
    habitat = db.Column(db.String, nullable=False, index=True)
    score = db.Column(db.Float, nullable=False)


class SandpiperCache(db.Model):
    __tablename__ = 'sandpiper_cache'
    key = db.Column(db.String, primary_key=True)
    value = db.Column(db.Text, nullable=False)
