from fastapi import APIRouter, Depends, status, HTTPException
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from slugify import slugify
from sqlalchemy import insert, select, update

from app.backend.db_depends import get_db
from app.sсhemas import CreateProduct
from app.models.products import Product
from app.models.category import Category
from app.routers.auth import get_current_user


router = APIRouter(prefix='/products', tags=['products'])


@router.get('/')
async def all_products(
        db: Annotated[AsyncSession, Depends(get_db)]
):
    products = await db.scalars(
        select(Product).where(Product.is_active == True, Product.stock > 0)
    )
    if products is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='There are no products'
        )
    return products.all()


@router.post('/', status_code=status.HTTP_201_CREATED)
async def create_product(
        db: Annotated[AsyncSession, Depends(get_db)],
        create_product: CreateProduct,
        get_user: Annotated[dict, Depends(get_current_user)]
):
    if get_user.get('is_admin') or get_user.get('id_customer'):
        category = await db.scalar(
            select(Category).where(Category.id == create_product.category)
        )

        if category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='There is no category found'
            )

        await db.execute(
            insert(Product).values(
                name=create_product.name,
                slug=slugify(create_product.name),
                description=create_product.description,
                price=create_product.price,
                image_url=create_product.image_url,
                stock=create_product.stock,
                category_id=create_product.category,
                rating=0.0,
                supplier_id=get_user.get('id')
            )
        )
        await db.commit()
        return {
            'status_code': status.HTTP_201_CREATED,
            'transaction': 'Successful'
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='You are not authorized to use this method'
        )


@router.get('/{category_slug}')
async def product_by_category(
        category_slug: str,
        db: Annotated[AsyncSession, Depends(get_db)]
):
    category = await db.scalar(
        select(Category).where(Category.slug == category_slug)
    )
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Category not found'
        )
    subcategories = await db.scalars(
        select(Category).where(Category.parent_id == category.id)
    )
    category_and_subcategories_id = [category.id] + [subcategory.id for subcategory in subcategories.all()]
    products = await db.scalars(
        select(Product).where(Product.category_id.in_(category_and_subcategories_id),
                              Product.is_active == True,
                              Product.stock > 0)
    )

    return products.all()


@router.get('/detail/{product_slug}')
async def product_detail(
        product_slug: str,
        db: Annotated[AsyncSession, Depends(get_db)]
):
    product = await db.scalar(
        select(Product).where(
            Product.slug == product_slug,
            Product.is_active == True,
            Product.stock > 0
        )
    )
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='There are no product'
        )

    return product


@router.put('/{product_slug}')
async def update_product(
        product_slug: str,
        update_product: CreateProduct,
        db: Annotated[AsyncSession, Depends(get_db)],
        get_user: Annotated[dict, Depends(get_current_user)]
):
    if get_user.get('is_admin') or get_user.get('is_customer'):
        product = await db.scalar(select(Product).where(Product.slug == product_slug))
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='There is no product found'
            )

        if get_user.get('is_admin') or product.supplier_id != get_user.get('id'):
            category = await db.scalar(select(Category).where(Category.id == update_product.category))
            if category is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='There is no category found'
                )

            await db.execute(
                update(Product).where(Product.slug == product_slug).values(
                    name=update_product.name,
                    slug=slugify(update_product.name),
                    description=update_product.description,
                    price=update_product.price,
                    image_url=update_product.image_url,
                    stock=update_product.stock,
                    category_id=update_product.category
                )
            )
            await db.commit()
            return {
                'status_code': status.HTTP_200_OK,
                'transaction': 'Product update is successful'
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='You are not authorized to use this method'
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='You are not authorized to use this method'
        )


@router.delete('/{product_slug}')
async def delete_product(
        product_slug: str,
        db: Annotated[AsyncSession, Depends(get_db)],
        get_user: Annotated[dict, Depends(get_current_user)]
):
    if get_user.get('is_admin') or get_user.get('is_supplier'):
        product = await db.scalar(
            select(Product).where(Product.slug == product_slug)
        )
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='There is no product found'
            )

        if get_user.get('is_admin') or product.supplier_id != get_user.get('id'):
            await db.execute(
                update(Product).where(Product.slug == product_slug).values(
                    is_active=False
                )
            )
            await db.commit()

            return {
                'status_code': status.HTTP_200_OK,
                'transaction': 'Products delete is successful'
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='You are not authorized to use this method'
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='You are not authorized to use this method'
        )
