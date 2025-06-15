Coworking space: Portlabs.co

instance write and update
from functools import cache

instance write

INSTANCES_FILENAME: str = "instances.json"

def update_model_instance(instance: EnrichMCP):
    raw_data: dict = instance.model_dump()
    if "__classname__" not in raw_data:
        raw_data["__classname__"] = instance.__class__.__name__

@cache
def get_enrichmcp_class_by_name(classname: str) ->Type[EnrichedMCP]:
    for enrichmcp_class in objs:
        if enrichmcp_class.__name__ ==. classname:
            return enrichmcp_class

def get_enrichmcp_class(raw_data: dict) -> Type[EnrichMCP]:
     return get_enrichmcp_class_by_name(raw_data.get("__classname__"))


@app.entity
class InstanceWithId(ErinchMCP):
    id: int
    instance: WorldBuilderEntity


def sort_files_by_ctime(pathname):
    """
    Used to ensure sort stability when preserving 
    original order.
    """
    files = glob.glob(pathname)
    return sorted(files, key=os.path.getctime)


def get_instances_filepath(entity_name: str) -> Path:
    return get_app_dir() / "instances" / entity_name / INSTANCES_FILENAME


def update_instance(id: int, instance: WorldBuilderEntity):
    instance_dicts: list[dict] =  json.loads(get_instances_filepath(world_builder_entity_name).read_text('utf-8'))
    try:
        instance_dicts[id] = instance.model_dump()
        get_instances_filepath(world_builder_entity_name).write_text(json.dumps(instance_dicts), 'utf-8')
    except KeyError:
        return None


def get_instance_by_id(id: int) -> Optional[WorldBuilderEntity]:
    instance_dicts: list[dict] =  json.loads(get_instances_filepath(world_builder_entity_name).read_text('utf-8'))
    try:
        return instance_dicts[id]
    except KeyError:
        return None


def list_entity_instances(world_builder_entity_name: str) -> list[InstanceWithId]:
    """world_builder_entity_name is the exact class name of the correct pydantic model"""
    model_instances: list[InstanceWithId] = []
    instance_dicts: list[dict] =  json.loads(get_instances_filepath(world_builder_entity_name).read_text('utf-8'))
    for index, instance_dict in enumerate(instance_dicts):
         instance_raw = json.loads(Path(entry).read_text('utf-8'))
         classname: Optional[str] = instance_raw.pop("__classname__")
         cls: Type[EnrichedMCP] = get_enrichmcp_class_by_name(classname)
         if cls is None:
             continue

         model_instances.append(InstanceWithId(id=index, instance=cls.model_validate(instance_raw)))
    return model_instances



def list_world_builder_entity_class_names() -> list[str]:
    """List model names when attempting to identify a model
    by a user-given description."""
    class_names: list[str] = []
    for enrichmcp_class in objs:
        class_names.append(enrichmcp_class.__name__)
    return class_names


RelationshipCardinality = Literal["one_to_one", "one_to_many", "many_to_one", "many_to_many"]


@app.entity
class EntitySchemaRelationship():
    world_builder_entity_name_one: str
    world_builder_entity_name_two: str


@app.entity
class InstanceRelationship():
    instance_id_one: int
    instance_id_two: int
    cardanlity: RelationshipCardinality


class Notice():
    message: str


@app.resource
def get_last_inserted_instance_id():
    pass


# def add_model_type should take create_relationship: Optional[Relationship] 
# instances will love in one file so that their

# model instances should be listed with ids for retrieval
# 
# create the instance and if there are undefined relationships remind it
# "Notice:"" to review prompt for those relationships



def add_relationship_to_entity_schema(relationship: EntitySchemaRelationship):
    pass




def add_relationship_between_instances(InstanceRelationship):
    pass


def has_empty_relationship(instance: WorldBuilderModel):
    # Returns if an instance has a relationship field
    # with no value.
    pass


def add_model_instance(instance: WorldBuilderModel) -> Optional[Notice]:
    instance_dicts: list[dict] =  json.loads(get_instances_filepath(instance.__class__.__name__).read_text('utf-8'))
    instance_dicts.append(instance)
    get_instances_filepath(instance.__class__.__name__).write_text(json.dumps(instance_dicts), 'utf-8')
    if has_empty_relationship(instance):

    return Notice(message="Created.  Review prompt and add relationship data between two instances if applicable.")

# if instance has unpopulated relationship