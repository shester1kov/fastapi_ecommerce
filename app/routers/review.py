from fastapi import HTTPException, status, Depends, APIRouter
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select, update, func
from sqlalchemy.orm import joinedload, selectinload

from app.backend.db_depends import get_db
from app.sсhemas import CreateReview
from app.models.products import Product
from app.models.review import Review
from app.models.rating import Rating
from app.routers.auth import get_current_user


router = APIRouter(prefix='/reviews', tags=['reviews'])


@router.get('/', status_code=status.HTTP_200_OK)
async def all_reviews(db: Annotated[AsyncSession, Depends(get_db)]):
    query = select(Review).options(joinedload(Review.rating)).where(Review.is_active == True)
    result = await db.execute(query)
    reviews = result.scalars().all()

    if not reviews:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Reviews not found'
        )

    response = [
        {
            'review_id': review.id,
            'comment': review.comment,
            'comment_date': review.comment_date,
            'user_id': review.user_id,
            'product_id': review.product_id,
            'rating': review.rating.grade
        } for review in reviews
    ]
    await db.commit()

    return response


@router.get('/{product_slug}', status_code=status.HTTP_200_OK)
async def products_reviews(
        product_slug: str,
        db: Annotated[AsyncSession, Depends(get_db)]
):
    product = await db.scalar(
        select(Product).where(Product.is_active == True, Product.stock > 0, Product.slug == product_slug)
    )

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Product not found'
        )

    query = select(Review).options(selectinload(Review.rating)).where(Review.is_active == True, Review.product_id == product.id)
    result = await db.execute(query)
    reviews = result.scalars().all()

    if not reviews:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='No reviews for this product'
        )

    response = [
        {
            'review_id': review.id,
            'comment': review.comment,
            'comment_date': review.comment_date,
            'user_id': review.user_id,
            'product_id': review.product_id,
            'rating': review.rating.grade

        } for review in reviews
    ]

    return response


@router.post('/{product_slug}', status_code=status.HTTP_201_CREATED)
async def add_review(
        product_slug: str,
        create_review: CreateReview,
        db: Annotated[AsyncSession, Depends(get_db)],
        get_user: Annotated[dict, Depends(get_current_user)]
):
    if create_review.grade > 5 or create_review.grade < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Rating must be between 1 and 5'
        )

    if get_user.get('is_customer'):
        product = await db.scalar(
            select(Product).where(Product.slug == product_slug, Product.is_active == True)
        )

        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='There is no product found'
            )

        existing_review = await db.scalar(
            select(Review).where(
                Review.is_active == True,
                Review.product_id == product.id,
                Review.user_id == get_user.get('id')
            )
        )

        if existing_review:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='You already have a review for this product'
            )

        rating = Rating(
            grade=create_review.grade,
            user_id=get_user.get('id'),
            product_id=product.id
        )

        review = Review(
            user_id=get_user.get('id'),
            product_id=product.id,
            rating=rating,
            comment=create_review.comment
        )

        db.add_all([rating, review])

        avg_rating = await db.scalar(
            select(func.avg(Rating.grade)).where(Rating.product_id == product.id, Rating.is_active == True)
        )

        product.rating = avg_rating

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


@router.delete('/{product_slug}/{review_id}')
async def delete_review(
        product_slug: str,
        review_id: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        get_user: Annotated[dict, Depends(get_current_user)]
):
    if get_user.get('is_admin'):
        product = await db.scalar(
            select(Product).where(Product.slug == product_slug, Product.is_active == True)
        )

        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Product not found'
            )

        review = await db.scalar(
            select(Review).where(Review.id == review_id, Review.product_id == product.id)
        )

        if review is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Review not found'
            )

        rating = await db.scalar(
            select(Rating).where(Rating.id == review.rating_id, Rating.product_id == product.id)
        )

        if rating is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Rating not found'
            )

        review.is_active = False
        rating.is_active = False

        avg_rating = await db.scalar(
            select(func.avg(Rating.grade)).where(Rating.product_id == product.id, Rating.is_active == True)
        )

        if avg_rating is None:
            product.rating = 0.0
        else:
            product.rating = avg_rating

        await db.commit()
        return {
            'status_code': status.HTTP_200_OK,
            'transaction': 'Successful'
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='You are not authorized to use this method'
        )
